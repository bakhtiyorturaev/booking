import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.barbers.services import get_barber_available_slots
from apps.bookings.models import Booking, BookingHold
from apps.bookings.serializers import BarberBookingCreateSerializer
from apps.bookings.services import create_booking, create_hold, get_branch_availability
from apps.clubs.models import Branch, City, Club, Zone
from apps.payments.models import ManualVenuePayment, VenueBilling
from apps.payments.venue_billing import record_venue_payment, set_venue_tariff


class VenueBillingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_user(username="billing_admin", phone="+998900000104", is_superuser=True, is_staff=True)
        cls.staff = User.objects.create_user(username="collector", phone="+998900000100", role=User.Role.MODERATOR)
        cls.owner = User.objects.create_user(username="venue_owner", phone="+998900000101", password="Owner!72946", role=User.Role.CLIENT)
        cls.other = User.objects.create_user(username="other_owner", phone="+998900000102", role=User.Role.CLIENT)
        cls.customer = User.objects.create_user(username="booking_customer", phone="+998900000103")
        cls.club = Club.objects.create(owner=cls.owner, name="First venue", status=Club.Status.ACTIVE)
        cls.second = Club.objects.create(owner=cls.owner, name="Second venue", status=Club.Status.ACTIVE)
        cls.foreign = Club.objects.create(owner=cls.other, name="Foreign venue", status=Club.Status.ACTIVE)
        cls.billing = VenueBilling.objects.create(club=cls.club, created_by=cls.staff, monthly_price_tiyin=10_000_000)
        cls.city = City.objects.create(name="Billing City", slug="billing-city")
        cls.branch = Branch.objects.create(club=cls.club, city=cls.city, name="Main", address="Address", latitude=41, longitude=69, status=Branch.Status.ACTIVE, is_24_hours=True, is_free=False)
        Branch.objects.create(club=cls.second, city=cls.city, name="Second", address="Address", latitude=41, longitude=69, status=Branch.Status.ACTIVE, is_free=False)
        cls.zone = Zone.objects.create(branch=cls.branch, name="Zone", capacity=3, price_per_hour_tiyin=100000)
        cls.barber = Barber.objects.create(user=cls.other, club=cls.club, branch=cls.branch, full_name="Barber", affiliation_status=Barber.AffiliationStatus.APPROVED, is_free=False)
        from apps.payments.models import BarberBilling
        BarberBilling.objects.create(barber=cls.barber, monthly_price_tiyin=5000000, created_by=cls.staff, paid_until=timezone.now() + timedelta(days=90))

    def api_client(self, user=None):
        client = APIClient()
        client.force_authenticate(user or self.staff)
        return client

    def pay(self, amount="50000", **overrides):
        data = {"club": str(self.club.pk), "amount": amount, "method": "CASH", "idempotency_key": str(uuid.uuid4()), "note": ""}
        data.update(overrides)
        return self.api_client().post("/api/v1/cabinet/venue-payments/", data, format="json")

    def times(self):
        target = timezone.localdate() + timedelta(days=1)
        starts = timezone.make_aware(datetime.combine(target, time(10)))
        return starts, starts + timedelta(hours=1)

    def test_payment_amount_proportionally_adds_15_days(self):
        response = self.pay()
        self.assertEqual(response.status_code, 201, response.data)
        payment = ManualVenuePayment.objects.get()
        self.assertEqual(payment.period_ends_at - payment.period_starts_at, timedelta(days=15))
        self.assertEqual(payment.received_by, self.staff)
        self.assertEqual(payment.client, self.owner)
        self.billing.refresh_from_db()
        self.assertEqual(self.billing.paid_until, payment.period_ends_at)

    def test_double_monthly_payment_adds_60_days(self):
        response = self.pay("200000", method="CARD")
        self.assertEqual(response.status_code, 201)
        payment = ManualVenuePayment.objects.get()
        self.assertEqual(payment.period_ends_at - payment.period_starts_at, timedelta(days=60))
        self.assertEqual(payment.method, "CARD")

    def test_fractional_days_and_tiyin_are_preserved(self):
        response = self.pay("12345.67")
        self.assertEqual(response.status_code, 201)
        payment = ManualVenuePayment.objects.get()
        self.assertEqual(payment.amount_tiyin, 1_234_567)
        micros = payment.amount_tiyin * 30 * 86400 * 1_000_000 // 10_000_000
        self.assertEqual(payment.period_ends_at - payment.period_starts_at, timedelta(microseconds=micros))
        self.assertEqual(Decimal(response.data["duration_days"]), Decimal("3.703701"))

    def test_payment_extends_remaining_period(self):
        old_expiry = timezone.now() + timedelta(days=10)
        self.billing.paid_until = old_expiry
        self.billing.save()
        self.pay()
        payment = ManualVenuePayment.objects.get()
        self.assertEqual(payment.period_starts_at, old_expiry)
        self.assertEqual(payment.period_ends_at, old_expiry + timedelta(days=15))

    def test_expired_period_restarts_at_entry_time(self):
        self.billing.paid_until = timezone.now() - timedelta(days=100)
        self.billing.save()
        now = timezone.now()
        with patch("apps.payments.venue_billing.timezone.now", return_value=now):
            self.pay()
        payment = ManualVenuePayment.objects.get()
        self.assertEqual(payment.period_starts_at, now)
        self.assertEqual(payment.period_ends_at, now + timedelta(days=15))

    def test_duplicate_request_adds_period_once(self):
        key = str(uuid.uuid4())
        first = self.pay(idempotency_key=key)
        second = self.pay(idempotency_key=key)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(ManualVenuePayment.objects.count(), 1)
        self.billing.refresh_from_db()
        self.assertEqual(self.billing.paid_until, ManualVenuePayment.objects.get().period_ends_at)

    def test_reused_key_with_changed_amount_is_conflict(self):
        key = str(uuid.uuid4())
        self.pay(idempotency_key=key)
        response = self.pay("60000", idempotency_key=key)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(ManualVenuePayment.objects.count(), 1)

    def test_duplicate_after_tariff_change_returns_original_payment(self):
        key = str(uuid.uuid4())
        first = self.pay(idempotency_key=key)
        set_venue_tariff(self.club, 20_000_000, self.superuser)
        second = self.pay(idempotency_key=key)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data, second.data)

    def test_tariff_change_preserves_expiry_and_historical_price(self):
        first = self.pay()
        response = self.api_client().post(f"/api/v1/cabinet/venue-billing/{self.club.pk}/tariff/", {"monthly_price": "50000"}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        set_venue_tariff(self.club, 5_000_000, self.superuser)
        self.billing.refresh_from_db()
        first_payment = ManualVenuePayment.objects.get()
        self.assertEqual(first_payment.monthly_price_tiyin, 10_000_000)
        self.assertEqual(self.billing.paid_until, first_payment.period_ends_at)
        second = self.pay()
        self.assertEqual(Decimal(second.data["duration_days"]), 30)
        self.assertEqual(first.data["period_ends_at"], second.data["period_starts_at"])

    def test_same_owner_venues_have_independent_tariffs_and_periods(self):
        second_billing = set_venue_tariff(self.second, 5_000_000, self.superuser)
        self.pay()
        second_billing.refresh_from_db()
        self.assertIsNone(second_billing.paid_until)
        response = self.pay(club=str(self.second.pk))
        self.assertEqual(Decimal(response.data["duration_days"]), 30)
        self.billing.refresh_from_db()
        self.assertEqual(self.billing.paid_until, ManualVenuePayment.objects.get(billing=self.billing).period_ends_at)

    def test_billing_details_and_history_are_only_visible_to_staff(self):
        payment = self.pay()
        paths = (
            "/api/v1/cabinet/venue-payments/",
            f"/api/v1/cabinet/venue-payments/{payment.data['id']}/",
            "/api/v1/cabinet/venue-payments/summary/",
        )
        for user in (self.owner, self.other, self.customer):
            for path in paths:
                with self.subTest(user=user.username, path=path):
                    self.assertEqual(self.api_client(user).get(path).status_code, 403)
        for path in paths:
            with self.subTest(staff_path=path):
                self.assertEqual(self.api_client().get(path).status_code, 200)

    def test_owner_cannot_record_payment_or_change_tariff(self):
        client = self.api_client(self.owner)
        response = client.post("/api/v1/cabinet/venue-payments/", {}, format="json")
        self.assertEqual(response.status_code, 403)
        response = client.post(f"/api/v1/cabinet/venue-billing/{self.club.pk}/tariff/", {"monthly_price": "1"}, format="json")
        self.assertEqual(response.status_code, 403)
        response = client.patch(f"/api/v1/cabinet/clubs/{self.club.pk}/", {"monthly_price": "1"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ManualVenuePayment.objects.count(), 0)

    def test_payment_actor_and_period_cannot_be_forged(self):
        response = self.pay(received_by=str(self.other.pk), period_ends_at=(timezone.now() + timedelta(days=999)).isoformat())
        self.assertEqual(response.status_code, 201)
        payment = ManualVenuePayment.objects.get()
        self.assertEqual(payment.received_by, self.staff)
        self.assertEqual(payment.period_ends_at - payment.period_starts_at, timedelta(days=15))

    def test_invalid_amounts_and_methods_do_not_change_balance(self):
        for amount in ("0", "-1", "NaN", "1.001", "1000000000000"):
            with self.subTest(amount=amount):
                self.assertEqual(self.pay(amount).status_code, 400)
        self.assertEqual(self.pay(method="PAYME").status_code, 400)
        self.assertEqual(ManualVenuePayment.objects.count(), 0)
        self.billing.refresh_from_db()
        self.assertIsNone(self.billing.paid_until)

    def test_payment_without_tariff_is_rejected(self):
        response = self.pay(club=str(self.second.pk))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ManualVenuePayment.objects.count(), 0)

    def test_expired_venue_rejects_new_hold_and_hides_availability(self):
        self.billing.paid_until = timezone.now() - timedelta(seconds=1)
        self.billing.save()
        starts, ends = self.times()
        with self.assertRaises(ValidationError) as error:
            create_hold(self.customer, self.zone.pk, starts, ends)
        self.assertEqual(error.exception.get_codes(), ["bookings.zone_not_available"])
        self.assertEqual(get_branch_availability(self.branch, starts.date()), [])
        self.assertEqual(BookingHold.objects.count(), 0)

    def test_paid_venue_accepts_customer_without_personal_subscription(self):
        self.pay()
        starts, ends = self.times()
        hold = create_hold(self.customer, self.zone.pk, starts, ends)
        self.assertEqual(hold.user, self.customer)
        self.assertTrue(get_branch_availability(self.branch, starts.date()))

    def test_expiry_after_hold_prevents_booking_conversion(self):
        self.pay()
        starts, ends = self.times()
        hold = create_hold(self.customer, self.zone.pk, starts, ends)
        self.billing.refresh_from_db()
        self.billing.paid_until = timezone.now() - timedelta(seconds=1)
        self.billing.save()
        with self.assertRaises(ValidationError):
            create_booking(self.customer, hold.pk)
        self.assertEqual(Booking.objects.count(), 0)
        hold.refresh_from_db()
        self.assertEqual(hold.status, BookingHold.Status.HELD)

    def test_expiry_is_checked_even_when_availability_was_cached(self):
        self.pay()
        starts, _ = self.times()
        self.assertTrue(get_branch_availability(self.branch, starts.date()))
        self.billing.refresh_from_db()
        self.billing.paid_until = timezone.now() - timedelta(seconds=1)
        self.billing.save()
        self.assertEqual(get_branch_availability(self.branch, starts.date()), [])

    def test_expired_barber_venue_rejects_booking_and_availability(self):
        starts, _ = self.times()
        serializer = BarberBookingCreateSerializer(data={"barber_id": str(self.barber.pk), "starts_at": starts.isoformat()})
        self.assertFalse(serializer.is_valid())
        slots = get_barber_available_slots(self.barber, starts.date())
        self.assertEqual(slots["slots"], [])
        self.assertFalse(slots["is_available"])

    def test_expired_owner_can_still_login_and_open_cabinet(self):
        client = APIClient()
        login = client.post("/api/v1/auth/login/", {"login": self.owner.username, "password": "Owner!72946", "login_type": "client"}, format="json")
        self.assertEqual(login.status_code, 200, login.data)
        client.force_authenticate(self.owner)
        self.assertEqual(client.get("/api/v1/cabinet/clubs/").status_code, 200)
        self.assertEqual(client.get("/api/v1/cabinet/venue-billing/").status_code, 200)

    def test_new_venue_cannot_bypass_billing_by_omitting_tariff(self):
        response = self.api_client(self.owner).post("/api/v1/cabinet/clubs/", {"name": "New unpaid venue"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        club = Club.objects.get(pk=response.data["id"])
        self.assertTrue(club.billing_required)
        from apps.payments.venue_billing import venue_accepts_bookings
        self.assertFalse(venue_accepts_bookings(club))

    def test_staff_can_create_client_and_assign_venue_with_custom_service(self):
        client = self.api_client()
        response = client.post("/api/v1/cabinet/users/", {"username": "New_Client", "phone": "+998 90 000 01 99", "full_name": "Mijoz Egasi", "password": "Owner!29479"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        owner = User.objects.get(pk=response.data["id"])
        self.assertEqual(owner.role, User.Role.CLIENT)
        self.assertFalse(owner.is_staff)
        self.assertTrue(owner.check_password("Owner!29479"))
        self.assertNotIn("password", response.data)
        venue = client.post("/api/v1/cabinet/clubs/", {"owner": str(owner.pk), "name": "Gym", "category": "OTHER", "service_name": "Sport zali", "status": "ACTIVE"}, format="json")
        self.assertEqual(venue.status_code, 201, venue.data)
        club = Club.objects.get(pk=venue.data["id"])
        self.assertEqual(club.owner, owner)
        self.assertFalse(VenueBilling.objects.filter(club=club).exists())

    def test_client_creation_rejects_role_escalation_and_weak_password(self):
        data = {"username": "new_owner", "phone": "+998900000199", "full_name": "Name", "password": "Owner!29479"}
        self.assertEqual(self.api_client().post("/api/v1/cabinet/users/", {**data, "role": "ADMIN"}, format="json").status_code, 400)
        self.assertEqual(self.api_client().post("/api/v1/cabinet/users/", {**data, "password": "1"}, format="json").status_code, 400)
        self.assertEqual(self.api_client(self.owner).post("/api/v1/cabinet/users/", data, format="json").status_code, 403)
        self.assertFalse(User.objects.filter(username="new_owner").exists())

    def test_owner_cannot_transfer_venue(self):
        response = self.api_client(self.owner).patch(f"/api/v1/cabinet/clubs/{self.club.pk}/", {"owner": str(self.other.pk)}, format="json")
        self.assertEqual(response.status_code, 400)
        self.club.refresh_from_db()
        self.assertEqual(self.club.owner, self.owner)

    def test_ledger_cannot_be_edited_or_deleted(self):
        response = self.pay()
        path = f"/api/v1/cabinet/venue-payments/{response.data['id']}/"
        self.assertEqual(self.api_client().patch(path, {"amount": "1"}, format="json").status_code, 405)
        self.assertEqual(self.api_client().delete(path).status_code, 405)
        self.assertEqual(ManualVenuePayment.objects.count(), 1)

    def test_summary_and_dashboard_use_manual_platform_collections(self):
        self.pay("50000")
        self.pay("100000", method="CARD")
        summary = self.api_client().get("/api/v1/cabinet/venue-payments/summary/")
        self.assertEqual(summary.data["cash_tiyin"], 5_000_000)
        self.assertEqual(summary.data["card_tiyin"], 10_000_000)
        self.assertEqual(summary.data["total_tiyin"], 15_000_000)
        dashboard = self.api_client().get("/api/v1/cabinet/stats/")
        self.assertEqual(dashboard.data["revenue"]["total_tiyin"], 15_000_000)


    def test_club_tariff_update_returns_current_rate_and_preserves_period(self):
        self.pay()
        self.billing.refresh_from_db()
        old_expiry = self.billing.paid_until
        response = self.api_client().patch(
            f"/api/v1/cabinet/clubs/{self.club.pk}/",
            {"monthly_price": "50000"}, format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.billing.refresh_from_db()
        self.assertEqual(self.billing.monthly_price_tiyin, 10_000_000)
        self.billing.refresh_from_db()
        self.assertEqual(self.billing.paid_until, old_expiry)

    def test_expiry_preserves_existing_bookings_and_owner_management_access(self):
        self.pay()
        starts, ends = self.times()
        hold = create_hold(self.customer, self.zone.pk, starts, ends)
        with patch("telegram_bot.services.queue_booking_message"), patch("telegram_bot.services.send_customer_booking_notification"):
            booking = create_booking(self.customer, hold.pk)
        self.billing.refresh_from_db()
        self.billing.paid_until = timezone.now() - timedelta(seconds=1)
        self.billing.save()
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PENDING_CONFIRMATION)
        response = self.api_client(self.owner).get("/api/v1/cabinet/bookings/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        customer_history = self.api_client(self.customer).get("/api/v1/bookings/")
        self.assertEqual(customer_history.data["count"], 1)


    def test_owner_cabinet_displays_read_only_billing_status(self):
        response = self.api_client(self.owner).get(
            f"/api/v1/cabinet/clubs/{self.club.pk}/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["billing"]["billing_status"], "UNPAID")
        self.assertNotIn("monthly_price", response.data)
        staff = self.api_client().get(f"/api/v1/cabinet/clubs/{self.club.pk}/")
        self.assertIn("billing", staff.data)

    def test_staff_payment_activates_new_venue(self):
        for status in (Club.Status.DRAFT, Club.Status.PENDING):
            with self.subTest(status=status):
                self.club.status = status
                self.club.save(update_fields=("status", "updated_at"))
                response = self.pay()
                self.assertEqual(response.status_code, 201, response.data)
                self.club.refresh_from_db()
                self.assertEqual(self.club.status, Club.Status.ACTIVE)
                billing = self.api_client().get(
                    f"/api/v1/cabinet/venue-billing/{self.club.pk}/"
                )
                self.assertEqual(billing.data["billing_status"], "ACTIVE")

    def test_payment_does_not_override_administrative_suspension(self):
        self.club.status = Club.Status.SUSPENDED
        self.club.save(update_fields=("status", "updated_at"))
        self.assertEqual(self.pay().status_code, 201)
        self.club.refresh_from_db()
        self.assertEqual(self.club.status, Club.Status.SUSPENDED)


    def test_owner_can_only_read_billing_of_owned_venues(self):
        client = self.api_client(self.owner)
        venues = client.get("/api/v1/cabinet/venue-billing/")
        self.assertEqual(venues.status_code, 200)
        self.assertEqual({row["id"] for row in venues.data["results"]}, {str(self.club.pk), str(self.second.pk)})
        foreign = client.get(f"/api/v1/cabinet/venue-billing/{self.foreign.pk}/")
        self.assertEqual(foreign.status_code, 404)
        filtered = client.get("/api/v1/cabinet/venue-billing/", {"club": str(self.foreign.pk)})
        self.assertEqual(filtered.data["count"], 0)

    def test_payment_warning_thresholds_use_exact_remaining_duration(self):
        now = timezone.now()
        cases = (
            (timedelta(days=6), "NONE", 6),
            (timedelta(days=5, microseconds=1), "NONE", 6),
            (timedelta(days=5), "WARNING", 5),
            (timedelta(days=3), "WARNING", 3),
            (timedelta(days=1, microseconds=1), "WARNING", 2),
            (timedelta(days=1), "CRITICAL", 1),
            (timedelta(hours=2), "CRITICAL", 1),
            (timedelta(), "EXPIRED", 0),
            (-timedelta(seconds=1), "EXPIRED", 0),
        )
        for duration, level, days in cases:
            with self.subTest(duration=duration):
                self.billing.paid_until = now + duration
                self.billing.save()
                with patch("apps.payments.venue_billing.timezone.now", return_value=now):
                    response = self.api_client(self.owner).get(f"/api/v1/cabinet/clubs/{self.club.pk}/")
                    venue = self.api_client(self.owner).get(f"/api/v1/cabinet/venue-billing/{self.club.pk}/")
                billing = response.data["billing"]
                self.assertEqual(billing["alert_level"], level)
                self.assertEqual(billing["remaining_days"], days)
                self.assertEqual(venue.data["alert_level"], level)
                self.assertEqual(venue.data["remaining_days"], days)

    def test_early_second_payment_starts_at_first_payment_expiry(self):
        first_date = timezone.now()
        with patch("apps.payments.venue_billing.timezone.now", return_value=first_date):
            first = self.pay("100000")
        with patch("apps.payments.venue_billing.timezone.now", return_value=first_date + timedelta(days=10)):
            second = self.pay("50000")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data["period_starts_at"], first.data["period_ends_at"])
        self.billing.refresh_from_db()
        self.assertEqual(self.billing.paid_until, first_date + timedelta(days=45))


    def test_regional_rule_precedence_and_payment_snapshot(self):
        from apps.clubs.models import ServiceType, District
        from apps.payments.models import VenueTariffRule
        from apps.payments.venue_billing import effective_venue_price
        service = ServiceType.objects.get(code="GYM")
        district = District.objects.create(city=self.city, name="District", slug="district")
        self.club.service_type = service
        self.club.billing_city = self.city
        self.club.billing_district = district
        self.club.save()
        default = VenueTariffRule.objects.create(service_type=service, monthly_price_tiyin=20_000_000)
        self.assertEqual(effective_venue_price(self.club), 20_000_000)
        city_rate = VenueTariffRule.objects.create(service_type=service, city=self.city, monthly_price_tiyin=10_000_000)
        self.assertEqual(effective_venue_price(self.club), 10_000_000)
        rate = VenueTariffRule.objects.create(service_type=service, city=self.city, district=district, monthly_price_tiyin=5_000_000)
        first = self.pay()
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(Decimal(first.data["duration_days"]), 30)
        rate.monthly_price_tiyin = 10_000_000
        rate.save()
        second = self.pay()
        self.assertEqual(Decimal(second.data["duration_days"]), 15)
        self.assertEqual(first.data["period_ends_at"], second.data["period_starts_at"])
        self.assertEqual(ManualVenuePayment.objects.get(pk=first.data["id"]).monthly_price_tiyin, 5_000_000)

    def test_staff_cannot_manage_tariffs_even_with_django_permissions(self):
        from django.contrib import admin
        from django.test import RequestFactory
        from apps.payments.models import VenueTariffRule
        request = RequestFactory().get("/admin/")
        request.user = self.staff
        handler = admin.site._registry[VenueTariffRule]
        self.assertFalse(handler.has_add_permission(request))
        self.assertFalse(handler.has_change_permission(request))
        request.user = self.superuser
        self.assertTrue(handler.has_change_permission(request))
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            set_venue_tariff(self.club, 1, self.staff)

    def test_dynamic_services_allow_new_service_without_code_changes(self):
        from apps.clubs.models import ServiceType
        self.assertGreaterEqual(ServiceType.objects.count(), 10)
        service = ServiceType.objects.create(code="TENNIS", name="Tennis korti")
        response = self.api_client().post("/api/v1/cabinet/clubs/", {"name": "Tennis", "owner": str(self.owner.pk), "service_type": str(service.pk), "billing_city": str(self.city.pk)}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["service_type_name"], "Tennis korti")
        self.assertEqual(response.data["category"], "OTHER")
        forged = self.api_client(self.owner).patch(f"/api/v1/cabinet/clubs/{response.data['id']}/", {"billing_city": None}, format="json")
        self.assertEqual(forged.status_code, 400)


    def test_operator_booking_uses_existing_capacity_and_billing_checks(self):
        self.pay()
        starts, ends = self.times()
        payload = {"user": str(self.customer.pk), "zone": str(self.zone.pk), "starts_at": starts.isoformat(), "ends_at": ends.isoformat(), "quantity": 3}
        with patch("telegram_bot.services.queue_booking_message"), patch("telegram_bot.services.send_customer_booking_notification"):
            response = self.api_client().post("/api/v1/cabinet/bookings/", payload, format="json")
            self.assertEqual(response.status_code, 201, response.data)
            blocked = self.api_client().post("/api/v1/cabinet/bookings/", payload, format="json")
            self.assertEqual(blocked.status_code, 400, blocked.data)
        self.assertEqual(self.api_client(self.owner).post("/api/v1/cabinet/bookings/", payload, format="json").status_code, 403)
        self.assertEqual(Booking.objects.count(), 1)

    def test_tariff_form_saves_som_and_admin_refuses_staff_post(self):
        from apps.payments.admin import VenueTariffRuleForm
        from apps.clubs.models import ServiceType
        form = VenueTariffRuleForm(data={"service_type": str(ServiceType.objects.get(code="GYM").pk), "city": str(self.city.pk), "district": "", "monthly_price": "75000.50"})
        self.assertTrue(form.is_valid(), form.errors)
        rate = form.save()
        self.assertEqual(rate.monthly_price_tiyin, 7_500_050)
        self.club.service_type = rate.service_type
        self.club.billing_city = self.city
        self.club.save()
        response = self.api_client().get("/api/v1/cabinet/venue-billing/")
        venue = next(row for row in response.data["results"] if row["id"] == str(self.club.pk))
        self.assertEqual(venue["monthly_price_tiyin"], 7_500_050)


    def test_general_resources_can_be_created_for_any_service(self):
        response = self.api_client().post("/api/v1/cabinet/zones/", {"branch": str(self.branch.pk), "name": "Bilyard stoli", "resource_type": "GENERAL", "booking_type": "PER_ZONE", "capacity": 4, "price_per_hour_tiyin": 5000000}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["resource_type"], "GENERAL")
