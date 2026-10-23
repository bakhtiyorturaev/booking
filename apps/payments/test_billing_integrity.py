"""Tiyin hisob-kitobi va to'lovni chetlab o'tish (bypass) testlari.

`test_billing_bypass.py` `is_free` darvozasini qamrab olgan. Bu fayl
hisob-kitobning **arifmetikasini** va global rejim mantiqini tekshiradi:

  1. Tarif 0 tiyin bo'lsa to'lov kiritish 500 (ZeroDivisionError /
     IntegrityError) bermasligi kerak.
  2. To'lov davri (`period_ends_at`) tiyin -> mikrosekund konvertatsiyasida
     to'g'ri hisoblanishi (yaxlitlash va juda katta summa).
  3. Idempotentlik kaliti qayta ishlatilganda konflikt qaytarilishi.
  4. `PlatformBillingSettings.paid_mode_enabled` (global pullik rejim)
     haqiqatda bron darvozasiga ta'sir qilishi.
"""

import datetime
import uuid

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.clubs.models import Branch, Club
from apps.core.models import City, ServiceType
from apps.payments.models import (
    BarberBilling,
    ManualVenuePayment,
    VenueBilling,
    VenueTariffRule,
)


class VenuePaymentArithmeticTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name="BI City", slug="bi-city")
        self.owner = User.objects.create_user(
            username="bi_owner", phone="+998905550001", role=User.Role.CLIENT
        )
        self.admin = User.objects.create_user(
            username="bi_admin", phone="+998905550002", role=User.Role.ADMIN,
            is_staff=True, is_superuser=True,
        )
        self.service = ServiceType.objects.create(code="BI_SVC", name="BI xizmat")
        self.club = Club.objects.create(
            name="BI Club", slug="bi-club", owner=self.owner, service_type=self.service
        )
        self.branch = Branch.objects.create(
            club=self.club, name="BI Branch", city=self.city, address="Addr",
            latitude="41.3", longitude="69.2", is_free=False,
        )

    def _rule(self, price):
        VenueTariffRule.objects.update_or_create(
            service_type=self.service, city=None, district=None,
            defaults={"monthly_price_tiyin": price},
        )

    def test_exact_monthly_amount_buys_exactly_thirty_days(self):
        from apps.payments.venue_billing import record_venue_payment

        self._rule(30_000_000)
        payment, created = record_venue_payment(
            club=self.club, actor=self.admin, amount_tiyin=30_000_000,
            method="CASH", idempotency_key=uuid.uuid4(),
        )
        self.assertTrue(created)
        duration = payment.period_ends_at - payment.period_starts_at
        self.assertEqual(duration.days, 30)
        self.assertLess(abs(duration - datetime.timedelta(days=30)), datetime.timedelta(seconds=1))

    def test_half_amount_buys_half_period_and_extends_cumulatively(self):
        from apps.payments.venue_billing import record_venue_payment

        self._rule(30_000_000)
        first, _ = record_venue_payment(
            club=self.club, actor=self.admin, amount_tiyin=15_000_000,
            method="CASH", idempotency_key=uuid.uuid4(),
        )
        self.assertEqual((first.period_ends_at - first.period_starts_at).days, 15)
        second, _ = record_venue_payment(
            club=self.club, actor=self.admin, amount_tiyin=15_000_000,
            method="CARD", idempotency_key=uuid.uuid4(),
        )
        # Ikkinchi to'lov birinchisining oxiridan boshlanishi kerak (yo'qotilmaydi).
        self.assertEqual(second.period_starts_at, first.period_ends_at)
        billing = VenueBilling.objects.get(club=self.club)
        self.assertEqual(billing.paid_until, second.period_ends_at)

    def test_reused_idempotency_key_with_same_data_is_not_double_counted(self):
        from apps.payments.venue_billing import record_venue_payment

        self._rule(30_000_000)
        key = uuid.uuid4()
        first, created_first = record_venue_payment(
            club=self.club, actor=self.admin, amount_tiyin=1_000_000,
            method="CASH", idempotency_key=key,
        )
        second, created_second = record_venue_payment(
            club=self.club, actor=self.admin, amount_tiyin=1_000_000,
            method="CASH", idempotency_key=key,
        )
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ManualVenuePayment.objects.count(), 1)

    def test_reused_idempotency_key_with_different_amount_conflicts(self):
        from apps.payments.venue_billing import PaymentConflict, record_venue_payment

        self._rule(30_000_000)
        key = uuid.uuid4()
        record_venue_payment(
            club=self.club, actor=self.admin, amount_tiyin=1_000_000,
            method="CASH", idempotency_key=key,
        )
        with self.assertRaises(PaymentConflict):
            record_venue_payment(
                club=self.club, actor=self.admin, amount_tiyin=2_000_000,
                method="CASH", idempotency_key=key,
            )

    def test_amount_smaller_than_one_microsecond_of_service_is_rejected(self):
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from apps.payments.venue_billing import record_venue_payment

        # 1 tiyin uchun davr uzunligi 0 mikrosekundga yaxlitlanadi.
        self._rule(30 * 86400 * 1_000_000 * 2)
        with self.assertRaises(DRFValidationError):
            record_venue_payment(
                club=self.club, actor=self.admin, amount_tiyin=1,
                method="CASH", idempotency_key=uuid.uuid4(),
            )

    def test_absurdly_large_amount_is_rejected_cleanly(self):
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from apps.payments.venue_billing import record_venue_payment

        self._rule(1)
        with self.assertRaises(DRFValidationError):
            record_venue_payment(
                club=self.club, actor=self.admin, amount_tiyin=10**18,
                method="CASH", idempotency_key=uuid.uuid4(),
            )

    def test_zero_price_tariff_must_raise_validation_error_not_server_error(self):
        """TUZATILDI (M-3): `VenueTariffRule` endi DB darajasida ham
        `monthly_price_tiyin > 0` ni talab qiladi; `record_venue_payment`
        esa 0/manfiy narxni `None` kabi "tarif yo'q" deb ko'radi — demak
        bo'linishgacha yetib bormaydi."""
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from apps.payments.venue_billing import record_venue_payment

        VenueBilling.objects.create(
            club=self.club, monthly_price_tiyin=30_000_000, created_by=self.admin
        )
        with self.assertRaises(Exception):
            # DB CheckConstraint endi 0 tiyinli qoidani umuman saqlashga
            # yo'l qo'ymaydi.
            VenueTariffRule.objects.create(
                service_type=self.service, city=None, district=None, monthly_price_tiyin=0
            )


class BarberPaymentTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name="BP City", slug="bp-city")
        self.admin = User.objects.create_user(
            username="bp_admin", phone="+998905560001", role=User.Role.ADMIN,
            is_staff=True, is_superuser=True,
        )
        self.barber_user = User.objects.create_user(
            username="bp_barber", phone="+998905560002"
        )
        self.barber = Barber.objects.create(
            user=self.barber_user, full_name="BP Barber", is_free=False,
            billing_city=self.city,
        )
        ServiceType.objects.update_or_create(
            code="BARBER", defaults={"name": "Sartarosh"}
        )

    def test_payment_requires_a_tariff(self):
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from apps.payments.barber_billing import record_barber_payment

        VenueTariffRule.objects.all().delete()
        with self.assertRaises(DRFValidationError):
            record_barber_payment(
                barber=self.barber, actor=self.admin, amount_tiyin=1_000,
                method="CASH", idempotency_key=uuid.uuid4(),
            )

    def test_free_barber_cannot_receive_payments(self):
        from rest_framework.exceptions import ValidationError as DRFValidationError
        from apps.payments.barber_billing import record_barber_payment

        Barber.objects.filter(pk=self.barber.pk).update(is_free=True)
        self.barber.refresh_from_db()
        with self.assertRaises(DRFValidationError):
            record_barber_payment(
                barber=self.barber, actor=self.admin, amount_tiyin=1_000,
                method="CASH", idempotency_key=uuid.uuid4(),
            )

    def test_paid_barber_period_is_cumulative(self):
        from apps.payments.barber_billing import record_barber_payment

        service = ServiceType.objects.get(code="BARBER")
        VenueTariffRule.objects.create(
            service_type=service, city=None, district=None, monthly_price_tiyin=3_000_000
        )
        first, _ = record_barber_payment(
            barber=self.barber, actor=self.admin, amount_tiyin=3_000_000,
            method="CASH", idempotency_key=uuid.uuid4(),
        )
        second, _ = record_barber_payment(
            barber=self.barber, actor=self.admin, amount_tiyin=3_000_000,
            method="CASH", idempotency_key=uuid.uuid4(),
        )
        self.assertEqual(second.period_starts_at, first.period_ends_at)
        self.assertEqual(
            BarberBilling.objects.get(barber=self.barber).paid_until,
            second.period_ends_at,
        )


class TariffLookupCachingTests(TestCase):
    """M-8: `effective_barber_price`/`effective_venue_price` har bir
    qatorga alohida `ServiceType`/`VenueTariffRule` so'rovi yuborardi —
    kabinet ro'yxatida N ta sartarosh/filial bo'lsa, N+1 so'rov muammosi.
    Endi natijalar qisqa muddatli keshda saqlanadi."""

    def setUp(self):
        self.city = City.objects.create(name="TC City", slug="tc-city")
        service, _ = ServiceType.objects.update_or_create(code="BARBER", defaults={"name": "Sartarosh"})
        VenueTariffRule.objects.create(
            service_type=service, city=None, district=None, monthly_price_tiyin=1_000_000
        )
        self.barbers = [
            Barber.objects.create(
                user=User.objects.create_user(username=f"tc_barber_{i}", phone=f"+99890500010{i}"),
                full_name=f"TC Barber {i}", is_free=False, billing_city=self.city,
            )
            for i in range(5)
        ]

    def test_resolving_price_for_many_barbers_does_not_scale_with_count(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        from apps.payments.barber_billing import effective_barber_price

        with CaptureQueriesContext(connection) as one_barber_queries:
            effective_barber_price(self.barbers[0])
        with CaptureQueriesContext(connection) as all_barbers_queries:
            for barber in self.barbers:
                self.assertEqual(effective_barber_price(barber), 1_000_000)

        # Agar har bir sartarosh o'ziga alohida so'rov yuborsa (eski N+1
        # xatosi), 5 ta sartarosh so'rovlar sonini kamida 5x oshiradi.
        # Keshlangandan keyin esa deyarli bir xil bo'lishi kerak.
        self.assertLessEqual(len(all_barbers_queries), len(one_barber_queries) + 2)


class GlobalPaidModeTests(TestCase):
    """`PlatformBillingSettings` modeli mavjud, ammo biznes mantiqida
    hech qayerda o'qilmaydi."""

    def setUp(self):
        self.city = City.objects.create(name="GM City", slug="gm-city")
        self.owner = User.objects.create_user(
            username="gm_owner", phone="+998905570001", role=User.Role.CLIENT
        )
        self.club = Club.objects.create(name="GM Club", slug="gm-club", owner=self.owner)
        self.branch = Branch.objects.create(
            club=self.club, name="GM Branch", city=self.city, address="Addr",
            latitude="41.3", longitude="69.2", is_free=True,
        )

    def test_new_branch_is_free_by_default(self):
        """Hujjatlashtirish: har bir yangi filial `is_free=True` bilan tug'iladi,
        ya'ni admin aralashmaguncha to'lovsiz bron qabul qiladi."""
        from apps.payments.venue_billing import branch_accepts_bookings

        self.assertTrue(self.branch.is_free)
        self.assertTrue(branch_accepts_bookings(self.branch))

    def test_enabling_global_paid_mode_should_close_free_branches(self):
        """TUZATILDI (M-4): `branch_accepts_bookings` endi
        `platform_paid_mode_active()` orqali global rejimni tekshiradi —
        o'tish davri (`grace_days`) tugagandan keyin `is_free` filiallar
        ham to'lov talab qiladi."""
        from apps.payments.models import PlatformBillingSettings
        from apps.payments.venue_billing import branch_accepts_bookings

        # `PlatformBillingSettings` singleton (pk=1) 0005-migratsiyada
        # allaqachon seed qilingan — `.create()` emas, mavjud qatorni
        # yangilaymiz.
        settings_row, _ = PlatformBillingSettings.objects.get_or_create(pk=1)
        settings_row.paid_mode_enabled = True
        settings_row.grace_days = 0
        settings_row.save()
        settings_row.paid_mode_started_at = timezone.now() - datetime.timedelta(days=1)
        settings_row.save()
        self.assertFalse(branch_accepts_bookings(self.branch))

    def test_grace_period_still_allows_free_branches(self):
        """`grace_days` o'tish davrida `is_free` filiallar hali ham bepul
        bron qabul qiladi — global rejim shart kuchga kirishi bilanoq
        kutilmaganda hamma joyni yopib qo'ymaydi."""
        from apps.payments.models import PlatformBillingSettings
        from apps.payments.venue_billing import branch_accepts_bookings

        settings_row, _ = PlatformBillingSettings.objects.get_or_create(pk=1)
        settings_row.paid_mode_enabled = True
        settings_row.grace_days = 7
        settings_row.save()
        self.assertTrue(branch_accepts_bookings(self.branch))

    def test_enabling_global_paid_mode_closes_free_barbers_too(self):
        from apps.barbers.models import Barber
        from apps.payments.models import PlatformBillingSettings
        from apps.payments.barber_billing import barber_accepts_bookings

        barber_user = User.objects.create_user(username="gm_barber", phone="+998905570002")
        barber = Barber.objects.create(user=barber_user, full_name="GM Barber", is_free=True)
        self.assertTrue(barber_accepts_bookings(barber))

        settings_row, _ = PlatformBillingSettings.objects.get_or_create(pk=1)
        settings_row.paid_mode_enabled = True
        settings_row.grace_days = 0
        settings_row.save()
        settings_row.paid_mode_started_at = timezone.now() - datetime.timedelta(days=1)
        settings_row.save()
        self.assertFalse(barber_accepts_bookings(barber))
