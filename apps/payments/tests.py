import hashlib
import hmac
import json
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.payments.models import Payment, SubscriptionPlan, UserSubscription
from apps.payments.services import has_paid_access


class SubscriptionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="subscription_user",
            phone="+998901234569",
        )

    def test_user_without_subscription_is_free(self):
        self.assertFalse(has_paid_access(self.user))

    def test_active_subscription_grants_paid_access(self):
        subscription = UserSubscription.objects.create(user=self.user)

        self.assertTrue(subscription.is_active)
        self.assertTrue(has_paid_access(self.user))
        self.assertAlmostEqual(
            subscription.expires_at - subscription.starts_at,
            timedelta(days=30),
            delta=timedelta(seconds=1),
        )

    def test_expired_subscription_is_free(self):
        UserSubscription.objects.create(
            user=self.user,
            starts_at=timezone.now() - timedelta(days=31),
            expires_at=timezone.now() - timedelta(days=1),
        )

        self.assertFalse(has_paid_access(self.user))

    def test_subscription_status_endpoint(self):
        UserSubscription.objects.create(user=self.user)
        client = APIClient()
        client.force_authenticate(self.user)

        response = client.get("/api/v1/subscriptions/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["plan"], "PAID")


class PaymentAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="payment_user",
            phone="+998901234570",
        )
        cls.plan = SubscriptionPlan.objects.create(
            code="premium-monthly",
            name="Premium 30 kun",
            price_tiyin=9_900_000,
            duration_days=30,
        )

    def authenticated_client(self):
        client = APIClient()
        client.force_authenticate(self.user)
        return client

    @override_settings(DEBUG=True, PAYMENT_PROVIDER="manual")
    def test_local_checkout_activates_subscription(self):
        response = self.authenticated_client().post(
            "/api/v1/payments/checkout/",
            {"plan_code": self.plan.code},
            format="json",
            HTTP_IDEMPOTENCY_KEY="checkout-1",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], Payment.Status.PAID)
        self.assertTrue(has_paid_access(self.user))

    @override_settings(DEBUG=True, PAYMENT_PROVIDER="manual")
    def test_checkout_is_idempotent(self):
        client = self.authenticated_client()
        first = client.post(
            "/api/v1/payments/checkout/",
            {"plan_code": self.plan.code},
            format="json",
            HTTP_IDEMPOTENCY_KEY="checkout-2",
        )
        second = client.post(
            "/api/v1/payments/checkout/",
            {"plan_code": self.plan.code},
            format="json",
            HTTP_IDEMPOTENCY_KEY="checkout-2",
        )

        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Payment.objects.filter(user=self.user).count(), 1)

    @override_settings(PAYMENT_WEBHOOK_SECRET="webhook-secret")
    def test_signed_webhook_marks_payment_paid(self):
        payment = Payment.objects.create(
            user=self.user,
            plan=self.plan,
            provider="http",
            idempotency_key="checkout-3",
            amount_tiyin=self.plan.price_tiyin,
        )
        payload = json.dumps(
            {
                "payment_id": str(payment.id),
                "external_id": "provider-123",
                "status": "PAID",
            }
        ).encode()
        signature = hmac.new(b"webhook-secret", payload, hashlib.sha256).hexdigest()

        response = APIClient().post(
            "/api/v1/payments/webhook/",
            data=payload,
            content_type="application/json",
            HTTP_X_PAYMENT_SIGNATURE=signature,
        )

        self.assertEqual(response.status_code, 200, response.data)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PAID)
        self.assertTrue(has_paid_access(self.user))
