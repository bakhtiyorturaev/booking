import hashlib
import hmac
import uuid

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.payments.models import Payment, SubscriptionPlan, UserSubscription


def has_paid_access(user):
    if not user or not user.is_authenticated:
        return False
    now = timezone.now()
    return UserSubscription.objects.filter(
        user=user,
        status=UserSubscription.Status.ACTIVE,
        starts_at__lte=now,
        expires_at__gt=now,
    ).exists()


def require_paid_access(user):
    if not has_paid_access(user):
        raise ValidationError("payments.active_paid_subscription_required", code="payments.active_paid_subscription_required")


def get_subscription_status(user):
    subscription = UserSubscription.objects.filter(user=user).first()
    if subscription is None:
        return {"plan": "FREE", "status": "FREE", "expires_at": None}

    if subscription.is_active:
        return {
            "plan": "PAID",
            "status": subscription.status,
            "expires_at": subscription.expires_at,
        }
    return {
        "plan": "FREE",
        "status": (
            UserSubscription.Status.CANCELLED
            if subscription.status == UserSubscription.Status.CANCELLED
            else UserSubscription.Status.EXPIRED
        ),
        "expires_at": subscription.expires_at,
    }


def verify_webhook_signature(raw_body, signature):
    if not settings.PAYMENT_WEBHOOK_SECRET or not signature:
        return False
    expected = hmac.new(
        settings.PAYMENT_WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@transaction.atomic
def activate_subscription_for_payment(payment):
    get_user_model().objects.select_for_update().get(pk=payment.user_id)
    subscription, _ = UserSubscription.objects.get_or_create(user=payment.user)
    subscription.activate_for_days(payment.plan.duration_days)
    return subscription


@transaction.atomic
def mark_payment_paid(payment_id, external_id=""):
    payment = Payment.objects.select_for_update().select_related("user", "plan").get(
        pk=payment_id
    )
    if payment.status == Payment.Status.PAID:
        return payment
    if payment.status != Payment.Status.PENDING:
        raise ValidationError("payments.cannot_mark_paid", code="payments.cannot_mark_paid")
    if payment.external_id and external_id and payment.external_id != external_id:
        raise ValidationError("payments.provider_id_mismatch", code="payments.provider_id_mismatch")

    payment.status = Payment.Status.PAID
    payment.paid_at = timezone.now()
    if external_id:
        payment.external_id = external_id
    payment.save(update_fields=("status", "paid_at", "external_id", "updated_at"))
    activate_subscription_for_payment(payment)
    return payment


def create_checkout(user, plan_code, idempotency_key=None):
    try:
        plan = SubscriptionPlan.objects.get(code=plan_code, is_active=True)
    except SubscriptionPlan.DoesNotExist as error:
        raise ValidationError("payments.plan_not_found", code="payments.plan_not_found") from error

    idempotency_key = (
        hashlib.sha256(f"{user.pk}:{idempotency_key}".encode()).hexdigest()
        if idempotency_key
        else str(uuid.uuid4())
    )
    existing = Payment.objects.filter(
        user=user,
        idempotency_key=idempotency_key,
    ).first()
    if existing:
        return existing

    payment = Payment.objects.create(
        user=user,
        plan=plan,
        provider=settings.PAYMENT_PROVIDER,
        idempotency_key=idempotency_key,
        amount_tiyin=plan.price_tiyin,
    )

    if settings.PAYMENT_PROVIDER == "manual":
        if not settings.DEBUG:
            raise ValidationError("payments.provider_not_configured", code="payments.provider_not_configured")
        return mark_payment_paid(payment.id, external_id=f"local-{payment.id}")

    if settings.PAYMENT_PROVIDER != "http" or not settings.PAYMENT_API_URL:
        raise ValidationError("payments.provider_not_configured", code="payments.provider_not_configured")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Idempotency-Key": idempotency_key,
    }
    if settings.PAYMENT_API_TOKEN:
        headers["Authorization"] = f"Bearer {settings.PAYMENT_API_TOKEN}"
    try:
        response = requests.post(
            settings.PAYMENT_API_URL,
            json={
                "payment_id": str(payment.id),
                "amount_tiyin": payment.amount_tiyin,
                "currency": payment.currency,
                "description": plan.name,
                "callback_url": settings.PAYMENT_CALLBACK_URL,
                "return_url": settings.PAYMENT_RETURN_URL,
            },
            headers=headers,
            timeout=settings.PAYMENT_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=("status", "updated_at"))
        raise ValidationError("payments.provider_invalid_response", code="payments.provider_invalid_response") from error
    checkout_url = str(data.get("checkout_url", ""))
    external_id = str(data.get("external_id", ""))
    if not checkout_url or not external_id:
        raise ValidationError("payments.provider_invalid_response", code="payments.provider_invalid_response")
    payment.checkout_url = checkout_url
    payment.external_id = external_id
    payment.save(update_fields=("checkout_url", "external_id", "updated_at"))
    return payment


@transaction.atomic
def apply_payment_webhook(payment_id, status, external_id=""):
    if status == "PAID":
        return mark_payment_paid(payment_id, external_id=external_id)

    try:
        payment = Payment.objects.select_for_update().select_related("user").get(pk=payment_id)
    except Payment.DoesNotExist as error:
        raise ValidationError("payments.transaction_not_found", code="payments.transaction_not_found") from error

    status_map = {
        "FAILED": Payment.Status.FAILED,
        "CANCELLED": Payment.Status.CANCELLED,
        "REFUNDED": Payment.Status.REFUNDED,
    }
    if status not in status_map:
        raise ValidationError("payments.invalid_status", code="payments.invalid_status")

    if payment.status == Payment.Status.PAID:
        # To'langan to'lovni faqat REFUND o'zgartira oladi va obunani bekor qiladi.
        if status != "REFUNDED":
            return payment
        UserSubscription.objects.filter(user=payment.user).update(
            status=UserSubscription.Status.CANCELLED,
            updated_at=timezone.now(),
        )

    payment.status = status_map[status]
    if external_id and not payment.external_id:
        payment.external_id = external_id
    payment.save(update_fields=("status", "external_id", "updated_at"))
    return payment
