"""Manual platform billing for individual venues (independent of customer plans)."""
from datetime import timedelta
from math import ceil

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError, PermissionDenied

from apps.clubs.models import Club
from apps.payments.models import ManualVenuePayment, VenueBilling


class PaymentConflict(APIException):
    status_code = 409
    default_detail = "Bu to‘lov kaliti boshqa ma’lumotlar bilan ishlatilgan."
    default_code = "payments.idempotency_conflict"


def effective_venue_price(club):
    from apps.payments.models import VenueTariffRule
    if not club.service_type_id:
        billing = getattr(club, "billing", None)
        return billing.monthly_price_tiyin if billing else None
    rules = VenueTariffRule.objects.filter(service_type_id=club.service_type_id)
    rule = rules.filter(district_id=club.billing_district_id).first() if club.billing_district_id else None
    if rule is None and club.billing_city_id:
        rule = rules.filter(city_id=club.billing_city_id, district__isnull=True).first()
    if rule is None:
        rule = rules.filter(city__isnull=True, district__isnull=True).first()
    return rule.monthly_price_tiyin if rule else None


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


def venue_accepts_bookings(club):
    billing = VenueBilling.objects.filter(club_id=club.pk).first()
    return bool(billing and billing.paid_until and billing.paid_until > timezone.now())


def branch_accepts_bookings(branch):
    return branch.is_free or venue_accepts_bookings(branch.club)


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
    if price is None:
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
    if club.status in {Club.Status.DRAFT, Club.Status.PENDING}:
        club.status = Club.Status.ACTIVE
        club.save(update_fields=("status", "updated_at"))
    return payment, True
