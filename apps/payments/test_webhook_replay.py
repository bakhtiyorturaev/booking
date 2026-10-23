"""M-10: to'lov provayderi webhookini qayta yuborish (replay) obunani
ikki marta uzaytirib yubormasligi kerak. `mark_payment_paid` holatni
`select_for_update()` bilan qulflab, faqat PENDING -> PAID o'tishida bir
marta `activate_subscription_for_payment` chaqiradi — qayta yuborilgan
xabar `payment.status == PAID` bo'lgani uchun hech narsa qilmay qaytadi.
Bu fayl shu xatti-harakatni tasdiqlaydi (regressiya qulfi)."""
import hashlib
import hmac

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.payments.models import Payment, SubscriptionPlan, UserSubscription
from apps.payments.services import apply_payment_webhook, verify_webhook_signature


class PaymentWebhookReplayTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="wh_user", phone="+998905580001")
        self.plan = SubscriptionPlan.objects.create(
            code="monthly", name="Oylik", price_tiyin=50_000_00, duration_days=30,
        )
        self.payment = Payment.objects.create(
            user=self.user, plan=self.plan, provider="http",
            idempotency_key="wh-key-1", amount_tiyin=self.plan.price_tiyin,
        )

    def test_replaying_paid_webhook_does_not_extend_subscription_twice(self):
        apply_payment_webhook(self.payment.id, "PAID", external_id="ext-1")
        subscription = UserSubscription.objects.get(user=self.user)
        first_expiry = subscription.expires_at

        # Gateway e'tirofni (ack) olmay qolib, xuddi shu webhookni qayta
        # yuborishi odatiy holat — bu obunani ikkinchi marta uzaytirmasligi
        # kerak.
        apply_payment_webhook(self.payment.id, "PAID", external_id="ext-1")
        subscription.refresh_from_db()
        self.assertEqual(subscription.expires_at, first_expiry)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)

    def test_replaying_refunded_webhook_is_a_no_op_after_first_time(self):
        apply_payment_webhook(self.payment.id, "PAID", external_id="ext-1")
        apply_payment_webhook(self.payment.id, "REFUNDED", external_id="ext-1")
        UserSubscription.objects.filter(user=self.user).update(status=UserSubscription.Status.ACTIVE)

        # Qayta yuborilgan REFUNDED webhooki obunani yana CANCELLED qilib
        # yubormasligi kerak (u allaqachon REFUNDED holatida).
        apply_payment_webhook(self.payment.id, "REFUNDED", external_id="ext-1")
        subscription = UserSubscription.objects.get(user=self.user)
        self.assertEqual(subscription.status, UserSubscription.Status.ACTIVE)


class WebhookSignatureTests(TestCase):
    @override_settings(PAYMENT_WEBHOOK_SECRET="test-secret")
    def test_tampered_body_is_rejected(self):
        body = b'{"payment_id": "x", "status": "PAID"}'
        signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        self.assertTrue(verify_webhook_signature(body, signature))
        self.assertFalse(verify_webhook_signature(body + b" ", signature))

    @override_settings(PAYMENT_WEBHOOK_SECRET="")
    def test_unconfigured_secret_rejects_every_webhook(self):
        body = b'{"payment_id": "x", "status": "PAID"}'
        self.assertFalse(verify_webhook_signature(body, "anything"))
