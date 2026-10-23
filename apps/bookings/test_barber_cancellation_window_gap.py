"""Documents a real logic gap found during audit: barber bookings have no
free-cancellation-window enforcement, unlike zone bookings.

cancel_booking() (apps/bookings/services.py) only applies the
free_cancellation_minutes check when `booking.zone and booking.zone.branch`
is truthy:

    if not operator and booking.status == Booking.Status.CONFIRMED and booking.zone and booking.zone.branch:
        cancel_until = booking.starts_at - timedelta(minutes=booking.zone.branch.free_cancellation_minutes)
        if timezone.now() > cancel_until:
            raise ValidationError("bookings.cancel_too_late", ...)

Barber bookings have `booking.zone is None`, so this branch is skipped
entirely -- a customer can cancel a CONFIRMED barber appointment seconds
before it starts, with no restriction at all, even though the equivalent
zone booking would be blocked.

TUZATILDI (2026-10-23): `cancel_booking` endi `cancellation_deadline()`
yordamchisi orqali zona va sartarosh bronlarida bir xil oynani qo'llaydi
(filialsiz sartarosh uchun `STANDALONE_FREE_CANCELLATION_MINUTES`).
Shuning uchun @expectedFailure markeri olib tashlandi — bu endi oddiy
regressiya testi.
"""

from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.bookings.models import Booking
from apps.bookings.services import cancel_booking
from apps.clubs.models import Club


class BarberBookingCancellationWindowGapTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="qa_gap_owner", phone="+998901270001", role=User.Role.CLIENT)
        self.club = Club.objects.create(
            name="QA Gap Barbershop", slug="qa-gap-barbershop",
            category=Club.Category.BARBERSHOP, owner=self.owner, status=Club.Status.ACTIVE,
        )
        self.barber_user = User.objects.create_user(username="qa_gap_barber", phone="+998901270002")
        self.barber = Barber.objects.create(
            user=self.barber_user, full_name="QA Gap Barber", club=self.club,
            affiliation_status=Barber.AffiliationStatus.APPROVED, is_active=True,
        )
        self.customer = User.objects.create_user(username="qa_gap_customer", phone="+998901270003")

        starts_in_two_minutes = timezone.now() + timedelta(minutes=2)
        self.booking = Booking.objects.create(
            user=self.customer, barber=self.barber, starts_at=starts_in_two_minutes,
            ends_at=starts_in_two_minutes + timedelta(hours=1), quantity=1,
            unit_price_tiyin=0, total_price_tiyin=0, status=Booking.Status.CONFIRMED,
        )

    def test_cancelling_confirmed_barber_booking_minutes_before_start_should_be_rejected(self):
        with self.assertRaises(Exception):
            cancel_booking(self.customer, self.booking.pk, "last-second cancel", operator=False)
