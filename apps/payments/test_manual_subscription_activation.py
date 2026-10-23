"""H-10: pullik obuna (demak, sharh qoldirish huquqi) production muhitida
hech qachon faollashtirilmaydi, chunki haqiqiy onlayn to'lov provayderi
(`PAYMENT_PROVIDER=http` + `PAYMENT_API_URL`) ulanmagan — `create_checkout`
doim `payments.provider_not_configured` qaytaradi.

Bu fayl shu bo'shliqni yopadigan xodim-tomonidan-qayd-etiladigan (naqd/karta)
obuna faollashtirish oqimini tekshiradi: `apps.payments.subscription_billing`
va `/api/v1/cabinet/payments/activate-subscription/` kabinet endpointi.
"""
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.payments.models import ManualSubscriptionPayment, SubscriptionPlan, UserSubscription
from apps.payments.services import create_checkout, has_paid_access, require_paid_access
from apps.payments.subscription_billing import record_subscription_payment
from apps.payments.venue_billing import PaymentConflict


class SelfServiceCheckoutDeadEndTests(TestCase):
    """Online to'lov provayderi ulanmagan production muhitida self-service
    checkout har doim ishlamaydi (regressiya qulfi — shu sabab H-10 zarur)."""

    def setUp(self):
        self.user = User.objects.create_user(username="checkout_user", phone="+998907710001")
        SubscriptionPlan.objects.create(code="monthly", name="Oylik", price_tiyin=50_000_00, duration_days=30)

    def test_create_checkout_cannot_succeed_without_real_gateway(self):
        with self.assertRaises(DjangoValidationError) as error:
            create_checkout(self.user, "monthly")
        self.assertEqual(error.exception.code, "payments.provider_not_configured")


class RecordSubscriptionPaymentServiceTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="billing_staff", phone="+998907710002", role=User.Role.ADMIN, is_staff=True,
        )
        self.customer = User.objects.create_user(username="paying_customer", phone="+998907710003")
        self.plan = SubscriptionPlan.objects.create(
            code="monthly", name="Oylik", price_tiyin=50_000_00, duration_days=30,
        )

    def test_manual_payment_activates_subscription(self):
        self.assertFalse(has_paid_access(self.customer))

        payment, created = record_subscription_payment(
            user=self.customer, actor=self.staff, plan_code="monthly",
            method="CASH", idempotency_key=uuid.uuid4(),
        )
        self.assertTrue(created)
        self.assertEqual(payment.amount_tiyin, self.plan.price_tiyin)

        self.customer.refresh_from_db()
        self.assertTrue(has_paid_access(self.customer))

    def test_repeated_idempotency_key_with_same_payload_is_not_duplicated(self):
        key = uuid.uuid4()
        first, created_first = record_subscription_payment(
            user=self.customer, actor=self.staff, plan_code="monthly",
            method="CASH", idempotency_key=key,
        )
        second, created_second = record_subscription_payment(
            user=self.customer, actor=self.staff, plan_code="monthly",
            method="CASH", idempotency_key=key,
        )
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ManualSubscriptionPayment.objects.count(), 1)

    def test_repeated_idempotency_key_with_different_payload_conflicts(self):
        key = uuid.uuid4()
        record_subscription_payment(
            user=self.customer, actor=self.staff, plan_code="monthly",
            method="CASH", idempotency_key=key,
        )
        with self.assertRaises(PaymentConflict):
            record_subscription_payment(
                user=self.customer, actor=self.staff, plan_code="monthly",
                method="CARD", idempotency_key=key,
            )

    def test_unlocks_require_paid_access_without_online_checkout(self):
        """`apps.reviews.services.create_review` sharh yozishdan oldin aynan
        shu `require_paid_access` darvozasini chaqiradi — qo'lda to'lov
        qayd etilgandan so'ng bu darvoza endi to'sqinlik qilmaydi."""
        with self.assertRaises(DjangoValidationError) as error:
            require_paid_access(self.customer)
        self.assertEqual(error.exception.code, "payments.active_paid_subscription_required")

        record_subscription_payment(
            user=self.customer, actor=self.staff, plan_code="monthly",
            method="CASH", idempotency_key=uuid.uuid4(),
        )
        self.customer.refresh_from_db()
        require_paid_access(self.customer)  # endi ValidationError ko'tarmaydi


class ActivateSubscriptionCabinetEndpointTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="cab_admin", phone="+998907710005", role=User.Role.ADMIN, is_staff=True,
        )
        self.customer = User.objects.create_user(username="cab_customer", phone="+998907710006")
        SubscriptionPlan.objects.create(code="monthly", name="Oylik", price_tiyin=50_000_00, duration_days=30)
        self.api = APIClient()

    def test_ordinary_customer_cannot_activate_subscriptions(self):
        self.api.force_authenticate(self.customer)
        response = self.api.post(
            "/api/v1/cabinet/payments/activate-subscription/",
            {
                "user": str(self.customer.id), "plan": "monthly",
                "method": "CASH", "idempotency_key": str(uuid.uuid4()),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_activate_subscription_for_customer(self):
        self.api.force_authenticate(self.admin)
        response = self.api.post(
            "/api/v1/cabinet/payments/activate-subscription/",
            {
                "user": str(self.customer.id), "plan": "monthly",
                "method": "CASH", "idempotency_key": str(uuid.uuid4()),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(UserSubscription.objects.get(user=self.customer).is_active)
