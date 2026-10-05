from datetime import timedelta
from math import ceil

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.barbers.models import Barber
from apps.clubs.models import ServiceType
from apps.payments.models import BarberBilling, ManualVenuePayment, VenueTariffRule
from apps.payments.venue_billing import PaymentConflict


def effective_barber_price(barber):
    service = ServiceType.objects.filter(code="BARBER").first()
    if service is None:
        return None
    city_id = barber.billing_city_id or (barber.branch.city_id if barber.branch_id else None)
    district_id = barber.billing_district_id or (barber.branch.district_id if barber.branch_id else None)
    rules = VenueTariffRule.objects.filter(service_type=service)
    rule = rules.filter(district_id=district_id).first() if district_id else None
    if rule is None and city_id:
        rule = rules.filter(city_id=city_id, district__isnull=True).first()
    if rule is None:
        rule = rules.filter(city__isnull=True, district__isnull=True).first()
    return rule.monthly_price_tiyin if rule else None


def barber_billing_status(barber):
    billing = getattr(barber, "billing", None)
    remaining = (billing.paid_until - timezone.now()).total_seconds() if billing and billing.paid_until else None
    price = effective_barber_price(barber)
    if barber.is_free:
        status = "FREE"
    elif price is None:
        status = "UNCONFIGURED"
    elif remaining is None:
        status = "UNPAID"
    else:
        status = "EXPIRED" if remaining <= 0 else "ACTIVE"
    alert = "NONE"
    if status != "FREE" and remaining is not None:
        if remaining <= 0:
            alert = "EXPIRED"
        elif remaining <= 86400:
            alert = "CRITICAL"
        elif remaining <= 5 * 86400:
            alert = "WARNING"
    return {
        "is_free": barber.is_free,
        "monthly_price_tiyin": price,
        "paid_until": billing.paid_until if billing else None,
        "billing_status": status,
        "billing_enabled": not barber.is_free,
        "grace_until": None,
        "remaining_days": max(0, ceil(remaining / 86400)) if remaining is not None else None,
        "alert_level": alert,
    }


def barber_accepts_bookings(barber):
    if barber.is_free:
        return True
    billing = getattr(barber, "billing", None)
    return bool(billing and billing.paid_until and billing.paid_until > timezone.now())


def require_barber_access(barber):
    if not barber_accepts_bookings(barber):
        raise ValidationError("Sartarosh hozir yangi bron qabul qilmayapti.", code="bookings.zone_not_available")


@transaction.atomic
def record_barber_payment(*, barber, actor, amount_tiyin, method, idempotency_key, note=""):
    barber = Barber.objects.select_for_update().select_related("branch").get(pk=barber.pk)
    existing = ManualVenuePayment.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if existing.barber_billing_id is None or existing.barber_billing.barber_id != barber.pk or existing.received_by_id != actor.pk or existing.amount_tiyin != amount_tiyin or existing.method != method or existing.note != note:
            raise PaymentConflict()
        return existing, False
    if barber.is_free:
        raise ValidationError("Bepul rejimda to‘lov kiritilmaydi.")
    price = effective_barber_price(barber)
    if price is None:
        raise ValidationError({"barber": "payments.tariff_required"})
    billing, _ = BarberBilling.objects.select_for_update().get_or_create(barber=barber, defaults={"monthly_price_tiyin": price, "created_by": actor})
    starts_at = max(timezone.now(), billing.paid_until) if billing.paid_until else timezone.now()
    try:
        ends_at = starts_at + timedelta(microseconds=amount_tiyin * 30 * 86400 * 1_000_000 // price)
    except OverflowError as error:
        raise ValidationError({"amount": "payments.amount_too_large"}) from error
    if ends_at <= starts_at:
        raise ValidationError({"amount": "payments.invalid_amount"})
    payment = ManualVenuePayment.objects.create(barber_billing=billing, client=barber.user, received_by=actor, amount_tiyin=amount_tiyin, monthly_price_tiyin=price, method=method, idempotency_key=idempotency_key, period_starts_at=starts_at, period_ends_at=ends_at, note=note)
    billing.monthly_price_tiyin = price
    billing.paid_until = ends_at
    billing.save(update_fields=("monthly_price_tiyin", "paid_until", "updated_at"))
    return payment, True
