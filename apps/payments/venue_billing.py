"""Manual platform billing for individual venues (independent of customer plans)."""
from datetime import timedelta
from math import ceil

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied

from apps.clubs.models import Club
from apps.payments.models import ManualVenuePayment, VenueBilling

_TARIFF_RULES_CACHE_KEY = "venue_tariff_rules_v1"
_TARIFF_RULES_CACHE_TTL = 30


class PaymentConflict(APIException):
    status_code = 409
    default_detail = "Bu to‘lov kaliti boshqa ma’lumotlar bilan ishlatilgan."
    default_code = "payments.idempotency_conflict"


def clear_tariff_rules_cache():
    cache.delete(_TARIFF_RULES_CACHE_KEY)


def _cached_tariff_rules():
    # Kabinet ro'yxatlarida (masalan, 50 ta sartarosh) har bir qator uchun
    # alohida `VenueTariffRule` so'rovi yubormaslik uchun — bu jadval kichik
    # va kamdan-kam o'zgaradi, shuning uchun qisqa TTL bilan keshlab, keyin
    # Python ichida filtrlaymiz (N+1 o'rniga 1 marta o'qish).
    rules = cache.get(_TARIFF_RULES_CACHE_KEY)
    if rules is None:
        from apps.payments.models import VenueTariffRule
        rules = list(
            VenueTariffRule.objects.values(
                "service_type_id", "city_id", "district_id", "monthly_price_tiyin"
            )
        )
        cache.set(_TARIFF_RULES_CACHE_KEY, rules, timeout=_TARIFF_RULES_CACHE_TTL)
    return rules


def _resolve_tariff_price(service_type_id, city_id, district_id):
    if not service_type_id:
        return None
    candidates = [r for r in _cached_tariff_rules() if r["service_type_id"] == service_type_id]
    rule = None
    if district_id:
        rule = next((r for r in candidates if r["district_id"] == district_id), None)
    if rule is None and city_id:
        rule = next((r for r in candidates if r["district_id"] is None and r["city_id"] == city_id), None)
    if rule is None:
        rule = next((r for r in candidates if r["district_id"] is None and r["city_id"] is None), None)
    return rule["monthly_price_tiyin"] if rule else None


def effective_venue_price(club):
    if not club.service_type_id:
        billing = getattr(club, "billing", None)
        return billing.monthly_price_tiyin if billing else None
    return _resolve_tariff_price(club.service_type_id, club.billing_city_id, club.billing_district_id)


def venue_billing_status(club):
    billing = getattr(club, "billing", None)
    paid = club.branches.filter(is_free=False).exists()
    result = {
        "billing_enabled": paid,
        "grace_until": None,
        "monthly_price_tiyin": effective_venue_price(club),
        "paid_until": billing.paid_until if billing else None,
        "billing_status": "UNCONFIGURED",
        "remaining_days": None,
        "alert_level": "NONE",
    }
    if not paid:
        result["billing_status"] = "FREE"
        return result
    if billing is None:
        if result["monthly_price_tiyin"] is not None:
            result["billing_status"] = "UNPAID"
        return result
    if billing.paid_until is None:
        result["billing_status"] = "UNPAID"
        return result
    remaining = (billing.paid_until - timezone.now()).total_seconds()
    result["remaining_days"] = max(0, ceil(remaining / 86400))
    if remaining <= 0:
        result.update(billing_status="EXPIRED", alert_level="EXPIRED")
    else:
        result["billing_status"] = "ACTIVE"
        if remaining <= 86400:
            result["alert_level"] = "CRITICAL"
        elif remaining <= 5 * 86400:
            result["alert_level"] = "WARNING"
    return result


def platform_paid_mode_active():
    """Platforma darajasidagi global pullik rejim haqiqatan ishga tushgan
    bo'lsa (yoqilgan + o'tish davri tugagan) `True` qaytaradi — shu payt
    individual `is_free=True` filial/sartaroshlar ham to'lov talab qiladi."""
    from apps.payments.models import PlatformBillingSettings
    settings_row = PlatformBillingSettings.objects.filter(pk=1).first()
    if not settings_row or not settings_row.paid_mode_enabled or not settings_row.paid_mode_started_at:
        return False
    grace_until = settings_row.paid_mode_started_at + timedelta(days=settings_row.grace_days)
    return timezone.now() >= grace_until


def venue_accepts_bookings(club):
    billing = VenueBilling.objects.filter(club_id=club.pk).first()
    return bool(billing and billing.paid_until and billing.paid_until > timezone.now())


def branch_accepts_bookings(branch):
    if branch.is_free and not platform_paid_mode_active():
        return True
    return venue_accepts_bookings(branch.club)


def require_branch_access(branch):
    if not branch_accepts_bookings(branch):
        raise ValidationError("Filial hozir yangi bron qabul qilmayapti.", code="bookings.zone_not_available")


@transaction.atomic
def set_venue_tariff(club, monthly_price_tiyin, actor):
    if not actor.is_superuser:
        raise PermissionDenied("Tarifni faqat superuser belgilaydi.")
    club = Club.objects.select_for_update().get(pk=club.pk)
    if not club.billing_required:
        club.billing_required = True
        club.save(update_fields=("billing_required", "updated_at"))
    billing, _ = VenueBilling.objects.get_or_create(
        club=club,
        defaults={"monthly_price_tiyin": monthly_price_tiyin, "created_by": actor},
    )
    billing.monthly_price_tiyin = monthly_price_tiyin
    billing.save(update_fields=("monthly_price_tiyin", "updated_at"))
    return billing


@transaction.atomic
def record_venue_payment(*, club, actor, amount_tiyin, method, idempotency_key, note=""):
    club = Club.objects.select_for_update().get(pk=club.pk)
    existing = ManualVenuePayment.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if (
            existing.billing_id is None
            or existing.billing.club_id != club.pk
            or existing.received_by_id != actor.pk
            or existing.amount_tiyin != amount_tiyin
            or existing.method != method
            or existing.note != note
        ):
            raise PaymentConflict()
        return existing, False

    if not club.branches.filter(is_free=False).exists():
        raise ValidationError("Bepul rejimda to‘lov kiritilmaydi.")
    price = effective_venue_price(club)
    if not price:
        # `price == 0` xuddi `None` kabi "tarif yo'q" deb hisoblanadi — aks
        # holda pastdagi bo'linish `ZeroDivisionError` (500) berardi.
        raise ValidationError({"club": "payments.tariff_required"})
    billing, _ = VenueBilling.objects.select_for_update().get_or_create(club=club, defaults={"monthly_price_tiyin": price, "created_by": actor})
    billing.monthly_price_tiyin = price
    now = timezone.now()
    starts_at = max(now, billing.paid_until) if billing.paid_until else now
    duration_microseconds = amount_tiyin * 30 * 86400 * 1_000_000 // billing.monthly_price_tiyin
    try:
        ends_at = starts_at + timedelta(microseconds=duration_microseconds)
    except OverflowError as error:
        raise ValidationError({"amount": "payments.amount_too_large"}) from error
    if ends_at <= starts_at:
        raise ValidationError({"amount": "payments.invalid_amount"})
    payment = ManualVenuePayment.objects.create(
        billing=billing,
        client=club.owner,
        received_by=actor,
        amount_tiyin=amount_tiyin,
        monthly_price_tiyin=billing.monthly_price_tiyin,
        method=method,
        idempotency_key=idempotency_key,
        period_starts_at=starts_at,
        period_ends_at=ends_at,
        note=note,
    )
    billing.paid_until = ends_at
    billing.save(update_fields=("monthly_price_tiyin", "paid_until", "updated_at"))
    return payment, True
