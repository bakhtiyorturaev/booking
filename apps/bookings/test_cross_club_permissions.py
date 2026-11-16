"""IDOR regression tests: one club/barber's operator must never be able to
act on another club/barber's booking.

transition_booking_for_operator() and cancel_booking(..., operator=True)
(apps/bookings/services.py) are the only two entry points club staff use to
confirm/check-in/complete/cancel a customer's booking from the cabinet. Both
resolve the booking's owning club/barber internally and must reject anyone
who is not that club's owner, that barber, or a platform admin.
"""

from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.bookings.models import Booking
from apps.bookings.services import cancel_booking, transition_booking_for_operator
from apps.clubs.models import Branch, City, Club, Zone


class CrossClubBookingPermissionTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name="QA Perm City", slug="qa-perm-city")

        self.owner_a = User.objects.create_user(username="qa_perm_owner_a", phone="+998901260001", role=User.Role.CLIENT)
        self.club_a = Club.objects.create(
            name="QA Perm Club A", slug="qa-perm-club-a",
            category=Club.Category.GAMING_CLUB, owner=self.owner_a, status=Club.Status.ACTIVE,
        )
        self.branch_a = Branch.objects.create(
            club=self.club_a, name="Branch A", city=self.city, address="Addr A",
            latitude="41.0", longitude="69.0", status=Branch.Status.ACTIVE, is_24_hours=True,
        )
        self.zone_a = Zone.objects.create(
            branch=self.branch_a, name="Zone A", capacity=5,
            booking_type=Zone.BookingType.PER_SEAT, price_per_hour_tiyin=10_000,
        )

        self.owner_b = User.objects.create_user(username="qa_perm_owner_b", phone="+998901260002", role=User.Role.CLIENT)
        self.club_b = Club.objects.create(
            name="QA Perm Club B", slug="qa-perm-club-b",
            category=Club.Category.GAMING_CLUB, owner=self.owner_b, status=Club.Status.ACTIVE,
        )

        self.customer = User.objects.create_user(username="qa_perm_customer", phone="+998901260003")

        tomorrow = timezone.localdate() + timedelta(days=1)
        starts_at = timezone.make_aware(datetime.combine(tomorrow, time(10, 0)))
        self.booking = Booking.objects.create(
            user=self.customer, zone=self.zone_a, starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1), quantity=1,
            unit_price_tiyin=10_000, total_price_tiyin=10_000,
            status=Booking.Status.PENDING_CONFIRMATION,
        )

    def test_other_club_owner_cannot_confirm_booking(self):
        with self.assertRaises(PermissionError):
            transition_booking_for_operator(self.owner_b, self.booking.pk, Booking.Status.CONFIRMED)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING_CONFIRMATION)

    def test_other_club_owner_cannot_cancel_booking(self):
        with self.assertRaises(PermissionError):
            cancel_booking(self.owner_b, self.booking.pk, "trying to cancel someone else's booking", operator=True)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING_CONFIRMATION)

    def test_owning_club_owner_can_confirm_booking(self):
        booking = transition_booking_for_operator(self.owner_a, self.booking.pk, Booking.Status.CONFIRMED)
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    def test_unrelated_barber_cannot_confirm_zone_booking(self):
        barber_user = User.objects.create_user(username="qa_perm_barber", phone="+998901260004")
        Barber.objects.create(
            user=barber_user, full_name="Unrelated Barber", club=self.club_b,
            affiliation_status=Barber.AffiliationStatus.APPROVED, is_active=True,
        )
        with self.assertRaises(PermissionError):
            transition_booking_for_operator(barber_user, self.booking.pk, Booking.Status.CONFIRMED)
