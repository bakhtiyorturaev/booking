import uuid
from datetime import time, timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.barbers.services import get_barber_available_slots
from apps.bookings.models import Booking
from apps.bookings.serializers import BarberBookingCreateSerializer
from apps.clubs.models import Branch, City, Club, ServiceType
from apps.payments.barber_billing import barber_accepts_bookings
from apps.payments.models import BarberBilling, ManualVenuePayment, VenueBilling, VenueTariffRule
from apps.payments.venue_billing import venue_accepts_bookings, branch_accepts_bookings


class PlatformAndBarberBillingTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="launcher", phone="+998901001001", role=User.Role.MODERATOR)
        self.owner = User.objects.create_user(username="salon_owner", phone="+998901001002", role=User.Role.CLIENT)
        self.customer = User.objects.create_user(username="customer", phone="+998901001003")
        self.other = User.objects.create_user(username="other_customer", phone="+998901001004")
        self.barber_user = User.objects.create_user(username="barber", phone="+998901001005", password="Barber!72946", role=User.Role.CLIENT)
        self.city = City.objects.create(name="Launch", slug="launch")
        self.club = Club.objects.create(owner=self.owner, name="Salon", category="BARBERSHOP", billing_required=True, status="ACTIVE")
        self.branch = Branch.objects.create(club=self.club, city=self.city, name="Salon branch", address="Address", latitude=41, longitude=69, status="ACTIVE", is_24_hours=True)
        self.barber = Barber.objects.create(user=self.barber_user, club=self.club, branch=self.branch, full_name="Barber", affiliation_status="APPROVED", working_days=[1, 2, 3, 4, 5, 6, 7])
        self.api = APIClient()
        self.api.force_authenticate(self.staff)
        self.rule = VenueTariffRule.objects.create(service_type=ServiceType.objects.get(code="BARBER"), monthly_price_tiyin=5_000_000)

    def enable_paid(self):
        self.branch.is_free = False
        self.branch.save()
        self.barber.is_free = False
        self.barber.save()

    def pay_barber(self, key=None, amount="50000"):
        return self.api.post("/api/v1/cabinet/venue-payments/", {"barber": str(self.barber.pk), "amount": amount, "method": "CASH", "idempotency_key": str(key or uuid.uuid4())}, format="json")

    def test_new_objects_start_free_and_can_be_switched_individually(self):
        self.assertTrue(branch_accepts_bookings(self.branch))
        self.assertTrue(barber_accepts_bookings(self.barber))
        self.assertEqual(self.pay_barber().status_code, 400)
        response = self.api.post(f"/api/v1/cabinet/branch-billing/{self.branch.pk}/free-mode/", {"is_free": False}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.branch.refresh_from_db()
        self.assertFalse(branch_accepts_bookings(self.branch))
        self.assertTrue(barber_accepts_bookings(self.barber))
        response = self.api.post(f"/api/v1/cabinet/barber-billing/{self.barber.pk}/free-mode/", {"is_free": False}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.barber.refresh_from_db()
        self.assertFalse(barber_accepts_bookings(self.barber))

    def test_free_mode_preserves_payment_period_and_other_branch_state(self):
        past = timezone.now() - timedelta(days=1)
        billing = VenueBilling.objects.create(club=self.club, created_by=self.staff, monthly_price_tiyin=10_000_000, paid_until=past)
        self.enable_paid()
        second = Branch.objects.create(club=self.club, city=self.city, name="Free second", address="Address", latitude=41, longitude=69)
        self.assertFalse(branch_accepts_bookings(self.branch))
        self.assertTrue(branch_accepts_bookings(second))
        response = self.api.post(f"/api/v1/cabinet/branch-billing/{self.branch.pk}/free-mode/", {"is_free": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.branch.refresh_from_db()
        self.assertTrue(branch_accepts_bookings(self.branch))
        billing.refresh_from_db()
        self.assertEqual(billing.paid_until, past)
        self.assertEqual(ManualVenuePayment.objects.count(), 0)

    def test_owners_and_customers_cannot_change_free_mode(self):
        for user in (self.owner, self.barber_user, self.customer):
            self.api.force_authenticate(user)
            for kind, instance in (("branch", self.branch), ("barber", self.barber)):
                response = self.api.post(f"/api/v1/cabinet/{kind}-billing/{instance.pk}/free-mode/", {"is_free": False}, format="json")
                self.assertEqual(response.status_code, 403)
        self.branch.refresh_from_db()
        self.barber.refresh_from_db()
        self.assertTrue(self.branch.is_free)
        self.assertTrue(self.barber.is_free)

    def test_barber_and_salon_payments_are_independent_and_retry_is_idempotent(self):
        self.enable_paid()
        salon = VenueBilling.objects.create(club=self.club, created_by=self.staff, monthly_price_tiyin=10_000_000, paid_until=timezone.now() + timedelta(days=5))
        self.assertFalse(barber_accepts_bookings(self.barber))
        key = uuid.uuid4()
        first = self.pay_barber(key)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(first.data["duration_days"], "30.000000")
        self.assertEqual(self.pay_barber(key).status_code, 200)
        second = self.pay_barber(amount="25000")
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(first.data["period_ends_at"], second.data["period_starts_at"])
        self.assertEqual(ManualVenuePayment.objects.count(), 2)
        salon.refresh_from_db()
        self.assertLess(salon.paid_until, timezone.now() + timedelta(days=6))
        self.assertTrue(barber_accepts_bookings(Barber.objects.get(pk=self.barber.pk)))

    def test_standalone_barber_has_no_dependency_on_salon_payment(self):
        self.barber.club = None
        self.barber.branch = None
        self.barber.billing_city = self.city
        self.barber.save()
        self.enable_paid()
        response = self.pay_barber()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(barber_accepts_bookings(Barber.objects.get(pk=self.barber.pk)))
        self.assertFalse(venue_accepts_bookings(self.club))

    def test_barber_owner_can_view_own_billing_but_cannot_record_payment(self):
        self.api.force_authenticate(self.barber_user)
        response = self.api.get("/api/v1/cabinet/barber-billing/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(self.api.get("/api/v1/cabinet/barbers/").status_code, 200)
        response = self.api.patch(f"/api/v1/cabinet/barbers/{self.barber.pk}/", {"work_start_time": "09:30", "work_end_time": "18:00", "working_days": [1, 3, 5]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.barber.refresh_from_db()
        self.assertEqual(self.barber.work_start_time, time(9, 30))
        self.assertEqual(self.barber.working_days, [1, 3, 5])
        self.assertEqual(self.pay_barber().status_code, 403)
        self.assertEqual(self.api.patch(f"/api/v1/cabinet/barbers/{self.barber.pk}/", {"billing_city": str(self.city.pk)}, format="json").status_code, 403)
        self.api.force_authenticate(self.other)
        self.assertEqual(self.api.get("/api/v1/cabinet/barber-billing/").data["count"], 0)
        self.assertEqual(self.api.patch(f"/api/v1/cabinet/barbers/{self.barber.pk}/", {"work_start_time": "10:00"}, format="json").status_code, 404)

    def test_barber_time_boundaries_and_two_prevalidated_requests(self):
        self.barber.work_start_time = time(9, 30)
        self.barber.work_end_time = time(11, 45)
        self.barber.save()
        tomorrow = timezone.localdate() + timedelta(days=1)
        slots = get_barber_available_slots(self.barber, tomorrow)["slots"]
        self.assertEqual([slot["time_label"] for slot in slots], ["09:30 - 10:30", "10:30 - 11:30"])
        data = {"barber_id": str(self.barber.pk), "starts_at": slots[0]["starts_at"]}
        first = BarberBookingCreateSerializer(data=data, context={"request": Mock(user=self.customer)})
        second = BarberBookingCreateSerializer(data=data, context={"request": Mock(user=self.other)})
        self.assertTrue(first.is_valid(), first.errors)
        self.assertTrue(second.is_valid(), second.errors)
        first.save()
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            second.save()
        self.assertEqual(Booking.objects.count(), 1)

    def test_barber_outside_working_hours_is_rejected(self):
        tomorrow = timezone.localdate() + timedelta(days=1)
        starts = timezone.make_aware(__import__("datetime").datetime.combine(tomorrow, time(3)))
        serializer = BarberBookingCreateSerializer(data={"barber_id": str(self.barber.pk), "starts_at": starts.isoformat()}, context={"request": Mock(user=self.customer)})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            serializer.save()


    def test_standalone_barber_manages_only_own_bookings(self):
        self.barber.club = None
        self.barber.branch = None
        self.barber.save()
        booking = Booking.objects.create(user=self.customer, barber=self.barber, starts_at=timezone.now() - timedelta(minutes=2), ends_at=timezone.now() + timedelta(minutes=58), status=Booking.Status.CONFIRMED, quantity=1, unit_price_tiyin=0, total_price_tiyin=0)
        self.api.force_authenticate(self.barber_user)
        self.assertEqual(self.api.get("/api/v1/cabinet/bookings/").data["count"], 1)
        response = self.api.post(f"/api/v1/cabinet/bookings/{booking.pk}/check-in/")
        self.assertEqual(response.status_code, 200, response.data)
        self.api.force_authenticate(self.other)
        self.assertEqual(self.api.get(f"/api/v1/cabinet/bookings/{booking.pk}/").status_code, 404)
