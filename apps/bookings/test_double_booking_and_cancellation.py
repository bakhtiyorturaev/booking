"""Double-booking va bekor qilish oynasi (cancellation window) regressiya testlari.

Qamrab olingan xavfli nuqtalar:
  1. Zona sig'imi (`create_hold`) — ketma-ket va bir vaqtda kelgan so'rovlar
     `booking_capacity` dan oshib ketmasligi.
  2. `create_hold` ichida ResourceBlock va `is_free`/billing darvozasi.
  3. Hold -> Booking konvertatsiyasi bir martalik (`CONVERTED` hold qayta
     ishlatilmasligi) va muddati o'tgan hold rad etilishi.
  4. Sartarosh sloti (`create_barber_booking`) bitta slotga ikki marta
     bron qabul qilmasligi.
  5. Bekor qilish oynasi: zona bronida ishlaydi, sartarosh bronida esa
     HOZIRGI kodda umuman yo'q (gap) — `test_barber_...` bilan qayd etilgan.
  6. `process_booking_lifecycle` no-show qoidasi sartarosh bronlarini
     butunlay chetlab o'tadi (gap).
"""

import datetime
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.bookings.models import Booking, BookingHold
from apps.bookings.services import (
    cancel_booking,
    create_barber_booking,
    create_booking,
    create_hold,
    process_booking_lifecycle,
)
from apps.clubs.models import Branch, Club, ResourceBlock, Zone
from apps.core.models import City

TASHKENT = ZoneInfo("Asia/Tashkent")


def _next_slot(hour=10, days=1):
    """Ertangi kunning aniq soat boshidagi local vaqti (UTC aware)."""
    local_now = timezone.localtime(timezone.now(), TASHKENT)
    target = (local_now + datetime.timedelta(days=days)).date()
    return datetime.datetime.combine(target, datetime.time(hour, 0), TASHKENT)


class ZoneHoldCapacityTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name="DB City", slug="db-city")
        self.owner = User.objects.create_user(
            username="db_owner", phone="+998903330001", role=User.Role.CLIENT
        )
        self.club = Club.objects.create(
            name="DB Club", slug="db-club", owner=self.owner, status=Club.Status.ACTIVE
        )
        self.branch = Branch.objects.create(
            club=self.club, name="DB Branch", city=self.city, address="Addr",
            latitude="41.3", longitude="69.2", status=Branch.Status.ACTIVE,
            is_24_hours=True, slot_interval_minutes=60, minimum_booking_minutes=60,
        )
        self.zone = Zone.objects.create(
            branch=self.branch, name="Zona-1", capacity=1, unit_count=1,
            booking_type=Zone.BookingType.PER_SEAT, price_per_hour_tiyin=1_000_000,
            status=Zone.Status.ACTIVE,
        )
        self.user_a = User.objects.create_user(username="db_a", phone="+998903330002")
        self.user_b = User.objects.create_user(username="db_b", phone="+998903330003")
        self.starts_at = _next_slot()
        self.ends_at = self.starts_at + datetime.timedelta(hours=1)

    def test_second_hold_on_full_zone_is_rejected(self):
        create_hold(self.user_a, self.zone.pk, self.starts_at, self.ends_at)
        with self.assertRaises(ValidationError) as error:
            create_hold(self.user_b, self.zone.pk, self.starts_at, self.ends_at)
        self.assertEqual(error.exception.code, "bookings.insufficient_seats")
        self.assertEqual(
            BookingHold.objects.filter(zone=self.zone, status=BookingHold.Status.HELD).count(),
            1,
        )

    def test_quantity_cannot_exceed_zone_capacity(self):
        with self.assertRaises(ValidationError) as error:
            create_hold(self.user_a, self.zone.pk, self.starts_at, self.ends_at, quantity=2)
        self.assertEqual(error.exception.code, "bookings.invalid_quantity")

    def test_expired_hold_frees_the_seat_for_another_user(self):
        hold = create_hold(self.user_a, self.zone.pk, self.starts_at, self.ends_at)
        BookingHold.objects.filter(pk=hold.pk).update(
            expires_at=timezone.now() - datetime.timedelta(seconds=1)
        )
        # Boshqa foydalanuvchi o'rinni egallay oladi.
        create_hold(self.user_b, self.zone.pk, self.starts_at, self.ends_at)
        self.assertEqual(
            BookingHold.objects.filter(
                zone=self.zone, status=BookingHold.Status.HELD,
                expires_at__gt=timezone.now(),
            ).count(),
            1,
        )

    def test_resource_block_prevents_hold(self):
        ResourceBlock.objects.create(
            zone=self.zone, starts_at=self.starts_at, ends_at=self.ends_at,
            reason="Ta'mirlash", is_active=True,
        )
        with self.assertRaises(ValidationError) as error:
            create_hold(self.user_a, self.zone.pk, self.starts_at, self.ends_at)
        self.assertEqual(error.exception.code, "bookings.zone_closed_at_time")

    def test_hold_converts_to_booking_exactly_once(self):
        hold = create_hold(self.user_a, self.zone.pk, self.starts_at, self.ends_at)
        booking = create_booking(self.user_a, hold.pk)
        self.assertEqual(booking.status, Booking.Status.PENDING_CONFIRMATION)
        hold.refresh_from_db()
        self.assertEqual(hold.status, BookingHold.Status.CONVERTED)
        with self.assertRaises(ValidationError) as error:
            create_booking(self.user_a, hold.pk)
        self.assertEqual(error.exception.code, "bookings.hold_expired_or_used")
        self.assertEqual(Booking.objects.filter(zone=self.zone).count(), 1)

    def test_expired_hold_cannot_become_booking(self):
        hold = create_hold(self.user_a, self.zone.pk, self.starts_at, self.ends_at)
        BookingHold.objects.filter(pk=hold.pk).update(
            expires_at=timezone.now() - datetime.timedelta(seconds=1)
        )
        with self.assertRaises(ValidationError):
            create_booking(self.user_a, hold.pk)
        hold.refresh_from_db()
        self.assertEqual(hold.status, BookingHold.Status.EXPIRED)
        self.assertFalse(Booking.objects.filter(hold=hold).exists())

    def test_another_user_cannot_convert_someone_elses_hold(self):
        hold = create_hold(self.user_a, self.zone.pk, self.starts_at, self.ends_at)
        with self.assertRaises(BookingHold.DoesNotExist):
            create_booking(self.user_b, hold.pk)

    def test_unpaid_non_free_branch_cannot_be_held(self):
        from rest_framework.exceptions import ValidationError as DRFValidationError

        Branch.objects.filter(pk=self.branch.pk).update(is_free=False)
        self.branch.refresh_from_db()
        with self.assertRaises(DRFValidationError):
            create_hold(self.user_a, self.zone.pk, self.starts_at, self.ends_at)


class ZoneCancellationWindowTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name="CW City", slug="cw-city")
        self.owner = User.objects.create_user(
            username="cw_owner", phone="+998903340001", role=User.Role.CLIENT
        )
        self.club = Club.objects.create(name="CW Club", slug="cw-club", owner=self.owner)
        self.branch = Branch.objects.create(
            club=self.club, name="CW Branch", city=self.city, address="Addr",
            latitude="41.3", longitude="69.2", is_24_hours=True,
            free_cancellation_minutes=60,
        )
        self.zone = Zone.objects.create(
            branch=self.branch, name="CW Zona", capacity=2, price_per_hour_tiyin=100,
        )
        self.customer = User.objects.create_user(username="cw_cust", phone="+998903340002")

    def _booking(self, minutes_ahead, status=Booking.Status.CONFIRMED):
        starts_at = timezone.now() + datetime.timedelta(minutes=minutes_ahead)
        return Booking.objects.create(
            user=self.customer, zone=self.zone, starts_at=starts_at,
            ends_at=starts_at + datetime.timedelta(hours=1), status=status,
        )

    def test_cancel_inside_window_is_rejected(self):
        booking = self._booking(minutes_ahead=30)
        with self.assertRaises(ValidationError) as error:
            cancel_booking(self.customer, booking.pk)
        self.assertEqual(error.exception.code, "bookings.cancel_too_late")
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    def test_cancel_outside_window_is_allowed(self):
        booking = self._booking(minutes_ahead=180)
        cancel_booking(self.customer, booking.pk, reason="Rejam o'zgardi")
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_operator_may_cancel_inside_window(self):
        booking = self._booking(minutes_ahead=10)
        cancel_booking(self.owner, booking.pk, reason="Klub yopildi", operator=True)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_cancelled_booking_cannot_be_cancelled_again(self):
        booking = self._booking(minutes_ahead=300)
        cancel_booking(self.customer, booking.pk)
        with self.assertRaises(ValidationError) as error:
            cancel_booking(self.customer, booking.pk)
        self.assertEqual(error.exception.code, "bookings.only_confirmed_can_cancel")

    def test_foreign_user_cannot_cancel(self):
        booking = self._booking(minutes_ahead=300)
        stranger = User.objects.create_user(username="cw_str", phone="+998903340003")
        with self.assertRaises(Booking.DoesNotExist):
            cancel_booking(stranger, booking.pk)


class BarberSlotTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name="BS City", slug="bs-city")
        self.owner = User.objects.create_user(
            username="bs_owner", phone="+998903350001", role=User.Role.CLIENT
        )
        self.club = Club.objects.create(
            name="BS Club", slug="bs-club", owner=self.owner,
            category=Club.Category.BARBERSHOP,
        )
        self.branch = Branch.objects.create(
            club=self.club, name="BS Branch", city=self.city, address="Addr",
            latitude="41.3", longitude="69.2", is_24_hours=True,
            free_cancellation_minutes=60,
        )
        barber_user = User.objects.create_user(username="bs_barber", phone="+998903350002")
        self.barber = Barber.objects.create(
            user=barber_user, full_name="BS Barber", club=self.club, branch=self.branch,
            affiliation_status=Barber.AffiliationStatus.APPROVED,
            status=Barber.Status.AVAILABLE, is_active=True,
        )
        self.barber.refresh_from_db()
        self.user_a = User.objects.create_user(username="bs_a", phone="+998903350003")
        self.user_b = User.objects.create_user(username="bs_b", phone="+998903350004")
        self.starts_at = _next_slot(hour=10)
        self.ends_at = self.starts_at + datetime.timedelta(hours=1)

    def test_same_slot_cannot_be_booked_twice(self):
        create_barber_booking(self.user_a, self.barber.pk, self.starts_at, self.ends_at)
        with self.assertRaises(ValidationError):
            create_barber_booking(self.user_b, self.barber.pk, self.starts_at, self.ends_at)
        self.assertEqual(
            Booking.objects.filter(barber=self.barber, starts_at=self.starts_at).count(), 1
        )

    def test_slot_must_be_exactly_one_hour(self):
        with self.assertRaises(ValidationError) as error:
            create_barber_booking(
                self.user_a, self.barber.pk, self.starts_at,
                self.starts_at + datetime.timedelta(minutes=90),
            )
        self.assertEqual(error.exception.code, "bookings.invalid_time_range")

    def test_user_cannot_hold_two_active_bookings(self):
        create_barber_booking(self.user_a, self.barber.pk, self.starts_at, self.ends_at)
        later = self.starts_at + datetime.timedelta(hours=2)
        with self.assertRaises(ValidationError) as error:
            create_barber_booking(
                self.user_a, self.barber.pk, later, later + datetime.timedelta(hours=1)
            )
        self.assertEqual(error.exception.code, "bookings.active_booking_exists")

    def test_unapproved_affiliation_blocks_booking(self):
        Barber.objects.filter(pk=self.barber.pk).update(
            affiliation_status=Barber.AffiliationStatus.PENDING
        )
        with self.assertRaises(ValidationError):
            create_barber_booking(self.user_a, self.barber.pk, self.starts_at, self.ends_at)

    def test_break_status_should_not_expose_free_slots(self):
        """TUZATILDI (M-2): `get_barber_available_slots` endi `BREAK`
        holatini ham DAY_OFF/NOT_AT_WORK kabi hisobga oladi."""
        from apps.barbers.services import get_barber_available_slots

        Barber.objects.filter(pk=self.barber.pk).update(status=Barber.Status.BREAK)
        self.barber.refresh_from_db()
        result = get_barber_available_slots(self.barber, timezone.localdate())
        self.assertFalse(any(slot["is_available"] for slot in result["slots"]))

    def test_barber_booking_should_respect_cancellation_window(self):
        """Regressiya: ilgari `cancel_booking` oynani faqat `booking.zone`
        mavjud bo'lganda tekshirgan, sartarosh bronida (zone=None) mijoz bron
        boshlanishidan 1 daqiqa oldin ham bekor qilib ketar edi."""
        starts_at = timezone.now() + datetime.timedelta(minutes=5)
        booking = Booking.objects.create(
            user=self.user_a, barber=self.barber, starts_at=starts_at,
            ends_at=starts_at + datetime.timedelta(hours=1),
            status=Booking.Status.CONFIRMED,
        )
        with self.assertRaises(ValidationError) as error:
            cancel_booking(self.user_a, booking.pk)
        self.assertEqual(error.exception.code, "bookings.cancel_too_late")

    def test_lifecycle_should_mark_barber_no_shows(self):
        """Regressiya: `process_booking_lifecycle` no-show so'rovida
        `zone__isnull=False` filtri bo'lgani uchun sartarosh bronlari abadiy
        CONFIRMED qolib ketar edi."""
        starts_at = timezone.now() - datetime.timedelta(hours=2)
        booking = Booking.objects.create(
            user=self.user_a, barber=self.barber, starts_at=starts_at,
            ends_at=starts_at + datetime.timedelta(hours=1),
            status=Booking.Status.CONFIRMED,
        )
        process_booking_lifecycle()
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.NO_SHOW)
