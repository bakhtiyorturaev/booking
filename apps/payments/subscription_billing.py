"""Manual (xodim tomonidan qayd etilgan) mijoz obuna to'lovlari.

Haqiqiy onlayn to'lov provayderi (`PAYMENT_PROVIDER=http`) hali ulanmagan
production muhitida `create_checkout()` doim `payments.provider_not_configured`
qaytaradi — demak mijozlar o'z-o'zicha obuna sotib ololmaydi. Shu bo'shliqni
yopish uchun platforma xodimi (admin/moderator) naqd/karta orqali to'lovni
qabul qilib, shu yerdan obunani qo'lda faollashtiradi (xuddi
`venue_billing.record_venue_payment` / `barber_billing.record_barber_payment`
filiallar va sartaroshlar uchun qilgani kabi).
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.payments.models import ManualSubscriptionPayment, SubscriptionPlan, UserSubscription
from apps.payments.venue_billing import PaymentConflict


@transaction.atomic
def record_subscription_payment(*, user, actor, plan_code, method, idempotency_key, amount_tiyin=None, note=""):
    try:
        plan = SubscriptionPlan.objects.get(code=plan_code, is_active=True)
    except SubscriptionPlan.DoesNotExist as error:
        raise ValidationError({"plan": "payments.plan_not_found"}, code="payments.plan_not_found") from error

    resolved_amount = amount_tiyin if amount_tiyin is not None else plan.price_tiyin

    existing = ManualSubscriptionPayment.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if (
            existing.user_id != user.pk
            or existing.plan_id != plan.pk
            or existing.received_by_id != actor.pk
            or existing.amount_tiyin != resolved_amount
            or existing.method != method
            or existing.note != note
        ):
            raise PaymentConflict()
        return existing, False

    user = get_user_model().objects.select_for_update().get(pk=user.pk)
    subscription, _ = UserSubscription.objects.select_for_update().get_or_create(user=user)
    subscription.activate_for_days(plan.duration_days)

    payment = ManualSubscriptionPayment.objects.create(
        user=user,
        plan=plan,
        received_by=actor,
        amount_tiyin=resolved_amount,
        method=method,
        idempotency_key=idempotency_key,
        note=note,
    )
    return payment, True
