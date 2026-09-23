from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.bookings.models import Booking, BookingHold, Cancellation
from apps.bookings.services import (
    cancel_booking,
    create_booking,
    create_hold,
    get_branch_availability,
)
from rest_framework.test import APIClient

from apps.clubs.models import Branch, City, Club, OperatingHour, Zone
from apps.payments.models import UserSubscription
from telegram_bot.models import BranchTelegramBinding, TelegramGroup


class BookingModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="booking_user",
            phone="+998901234567",
        )
        cls.subscription = UserSubscription.objects.create(user=cls.user)
        club = Club.objects.create(
            owner=cls.user,
            name="Test Club",
            status=Club.Status.ACTIVE,
        )
        city = City.objects.create(name="Test City", slug="test-city")
        cls.branch = Branch.objects.create(
            club=club,
            city=city,
            name="Main",
            address="Test address",
            latitude=41,
            longitude=69,
            status=Branch.Status.ACTIVE,
        )
        cls.zone = Zone.objects.create(
            branch=cls.branch,
            name="Standard",
            capacity=5,
            price_per_hour_tiyin=2_000_000,
        )
        group = TelegramGroup.objects.create(name="Main group", chat_id=-1001234567890)
        BranchTelegramBinding.objects.create(branch=cls.branch, group=group)

    def make_hold(self, **overrides):
        starts_at = timezone.now() + timedelta(days=1)
        values = {
            "user": self.user,
            "zone": self.zone,
            "starts_at": starts_at,
            "ends_at": starts_at + timedelta(hours=1),
            "quantity": 1,
            "unit_price_tiyin": 2_000_000,
            "total_price_tiyin": 2_000_000,
            "expires_at": timezone.now() + timedelta(minutes=7),
        }
        values.update(overrides)
        return BookingHold.objects.create(**values)

    def test_booking_follows_allowed_transition(self):
        hold = self.make_hold()
        booking = Booking.objects.create(
            hold=hold,
            user=hold.user,
            zone=hold.zone,
            starts_at=hold.starts_at,
            ends_at=hold.ends_at,
            quantity=hold.quantity,
            unit_price_tiyin=hold.unit_price_tiyin,
            total_price_tiyin=hold.total_price_tiyin,
            status=Booking.Status.CONFIRMED,
        )

        booking.transition_to(Booking.Status.CHECKED_IN)

        self.assertEqual(booking.status, Booking.Status.CHECKED_IN)

    def test_booking_rejects_invalid_transition(self):
        hold = self.make_hold()
        booking = Booking.objects.create(
            hold=hold,
            user=hold.user,
            zone=hold.zone,
            starts_at=hold.starts_at,
            ends_at=hold.ends_at,
            quantity=hold.quantity,
            unit_price_tiyin=hold.unit_price_tiyin,
            total_price_tiyin=hold.total_price_tiyin,
        )

        with self.assertRaises(ValidationError):
            booking.transition_to(Booking.Status.COMPLETED)

    def test_hold_cannot_exceed_zone_capacity(self):
        hold = self.make_hold(quantity=self.zone.capacity + 1)

        with self.assertRaises(ValidationError):
            hold.full_clean()

    def test_room_booking_uses_room_count_and_whole_room_price(self):
        room = Zone.objects.create(
            branch=self.branch,
            name="VIP room",
            booking_type=Zone.BookingType.PER_ZONE,
            capacity=6,
            unit_count=2,
            price_per_hour_tiyin=12_000_000,
        )
        target_date = timezone.localdate() + timedelta(days=1)
        OperatingHour.objects.create(
            branch=self.branch,
            weekday=target_date.weekday(),
            opens_at="00:00",
            closes_at="23:59",
        )
        starts_at = timezone.make_aware(datetime.combine(target_date, time(hour=10)))

        hold = create_hold(
            self.user,
            room.id,
            starts_at,
            starts_at + timedelta(hours=1),
        )
        availability = get_branch_availability(self.branch, target_date)
        room_data = next(item for item in availability if item["zone"].id == room.id)
        slot = next(item for item in room_data["slots"] if item["starts_at"] == starts_at)

        self.assertEqual(hold.total_price_tiyin, room.price_per_hour_tiyin)
        self.assertEqual(slot["available"], 1)

        invalid_hold = self.make_hold(zone=room, quantity=room.unit_count + 1)
        with self.assertRaises(ValidationError):
            invalid_hold.full_clean()

    def test_expired_hold_is_marked_expired(self):
        hold = self.make_hold(expires_at=timezone.now() - timedelta(seconds=1))

        self.assertTrue(hold.expire())
        self.assertEqual(hold.status, BookingHold.Status.EXPIRED)

    def test_hold_and_booking_api_flow(self):
        local_now = timezone.localtime()
        target_date = local_now.date() + timedelta(days=1)
        OperatingHour.objects.create(
            branch=self.branch,
            weekday=target_date.weekday(),
            opens_at="00:00",
            closes_at="23:59",
        )
        starts_at = timezone.make_aware(
            datetime.combine(target_date, time(hour=10))
        )
        client = APIClient()
        client.force_authenticate(self.user)

        hold_response = client.post(
            "/api/v1/booking-holds/",
            {
                "zone_id": self.zone.id,
                "starts_at": starts_at.isoformat(),
                "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
                "quantity": 2,
            },
            format="json",
        )
        self.assertEqual(hold_response.status_code, 201)

        booking_response = client.post(
            "/api/v1/bookings/",
            {"hold_id": hold_response.data["id"]},
            format="json",
        )
        self.assertEqual(booking_response.status_code, 201)
        self.assertEqual(
            booking_response.data["status"],
            Booking.Status.PENDING_CONFIRMATION,
        )

    def test_confirmed_booking_can_be_cancelled(self):
        hold = self.make_hold()
        booking = Booking.objects.create(
            hold=hold,
            user=hold.user,
            zone=hold.zone,
            starts_at=hold.starts_at,
            ends_at=hold.ends_at,
            quantity=hold.quantity,
            unit_price_tiyin=hold.unit_price_tiyin,
            total_price_tiyin=hold.total_price_tiyin,
            status=Booking.Status.CONFIRMED,
        )
        client = APIClient()
        client.force_authenticate(self.user)

        response = client.post(
            f"/api/v1/bookings/{booking.id}/cancel/",
            {"reason": "Reja o‘zgardi"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Booking.Status.CANCELLED)
        self.assertTrue(hasattr(booking, "cancellation"))

    def test_user_cannot_create_second_active_hold(self):
        target_date = timezone.localdate() + timedelta(days=1)
        OperatingHour.objects.create(
            branch=self.branch,
            weekday=target_date.weekday(),
            opens_at="00:00",
            closes_at="23:59",
        )
        starts_at = timezone.make_aware(datetime.combine(target_date, time(hour=10)))
        client = APIClient()
        client.force_authenticate(self.user)
        payload = {
            "zone_id": self.zone.id,
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
            "quantity": 1,
        }

        self.assertEqual(
            client.post("/api/v1/booking-holds/", payload, format="json").status_code,
            201,
        )
        response = client.post("/api/v1/booking-holds/", payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "bookings.active_booking_exists")

    def test_booking_cannot_be_cancelled_less_than_one_hour_before_start(self):
        hold = self.make_hold(
            starts_at=timezone.now() + timedelta(minutes=30),
            ends_at=timezone.now() + timedelta(minutes=90),
        )
        booking = Booking.objects.create(
            hold=hold,
            user=hold.user,
            zone=hold.zone,
            starts_at=hold.starts_at,
            ends_at=hold.ends_at,
            quantity=hold.quantity,
            unit_price_tiyin=hold.unit_price_tiyin,
            total_price_tiyin=hold.total_price_tiyin,
            status=Booking.Status.CONFIRMED,
        )
        client = APIClient()
        client.force_authenticate(self.user)

        response = client.post(
            f"/api/v1/bookings/{booking.id}/cancel/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "bookings.cancel_too_late")

    def test_active_booking_blocks_another_hold(self):
        target_date = timezone.localdate() + timedelta(days=1)
        OperatingHour.objects.create(
            branch=self.branch,
            weekday=target_date.weekday(),
            opens_at="00:00",
            closes_at="23:59",
        )
        starts_at = timezone.make_aware(datetime.combine(target_date, time(hour=10)))
        first_hold = create_hold(
            self.user,
            self.zone.id,
            starts_at,
            starts_at + timedelta(hours=1),
        )
        create_booking(self.user, first_hold.id)

        with self.assertRaises(ValidationError) as error:
            create_hold(
                self.user,
                self.zone.id,
                starts_at + timedelta(hours=2),
                starts_at + timedelta(hours=3),
            )

        self.assertEqual(error.exception.code, "bookings.active_booking_exists")

    def test_cancelled_booking_immediately_releases_capacity(self):
        target_date = timezone.localdate() + timedelta(days=1)
        OperatingHour.objects.create(
            branch=self.branch,
            weekday=target_date.weekday(),
            opens_at="00:00",
            closes_at="23:59",
        )
        starts_at = timezone.make_aware(datetime.combine(target_date, time(hour=10)))
        hold = create_hold(
            self.user,
            self.zone.id,
            starts_at,
            starts_at + timedelta(hours=1),
            quantity=self.zone.capacity,
        )
        booking = create_booking(self.user, hold.id)

        before = get_branch_availability(self.branch, target_date)
        before_slot = next(
            slot
            for slot in before[0]["slots"]
            if slot["starts_at"] == starts_at
        )
        cancel_booking(self.user, booking.id)
        after = get_branch_availability(self.branch, target_date)
        after_slot = next(
            slot
            for slot in after[0]["slots"]
            if slot["starts_at"] == starts_at
        )

        self.assertEqual(before_slot["available"], 0)
        self.assertEqual(after_slot["available"], self.zone.capacity)

    def test_invalid_availability_date_returns_message_code(self):
        response = APIClient().get(
            f"/api/v1/branches/{self.branch.id}/availability/",
            {"date": "invalid-date"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "bookings.invalid_date_format")

    def test_booking_has_unique_twelve_digit_number(self):
        first = Booking.objects.create(
            hold=self.make_hold(),
            user=self.user,
            zone=self.zone,
            starts_at=timezone.now() + timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=1, hours=1),
            unit_price_tiyin=2_000_000,
            total_price_tiyin=2_000_000,
        )
        second = Booking.objects.create(
            hold=self.make_hold(),
            user=self.user,
            zone=self.zone,
            starts_at=timezone.now() + timedelta(days=2),
            ends_at=timezone.now() + timedelta(days=2, hours=1),
            unit_price_tiyin=2_000_000,
            total_price_tiyin=2_000_000,
        )

        self.assertEqual(len(first.booking_number), 12)
        self.assertTrue(first.booking_number.isdigit())
        self.assertNotEqual(first.booking_number, second.booking_number)

    def test_free_user_cannot_create_hold(self):
        self.subscription.delete()
        target_date = timezone.localdate() + timedelta(days=1)
        OperatingHour.objects.create(
            branch=self.branch,
            weekday=target_date.weekday(),
            opens_at="00:00",
            closes_at="23:59",
        )
        starts_at = timezone.make_aware(datetime.combine(target_date, time(hour=10)))
        client = APIClient()
        client.force_authenticate(self.user)

        response = client.post(
            "/api/v1/booking-holds/",
            {
                "zone_id": self.zone.id,
                "starts_at": starts_at.isoformat(),
                "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "payments.active_paid_subscription_required")

    def test_free_user_sees_active_booking_and_last_three_history_items(self):
        self.subscription.delete()
        for day in range(1, 6):
            hold = self.make_hold(
                starts_at=timezone.now() - timedelta(days=day, hours=1),
                ends_at=timezone.now() - timedelta(days=day),
            )
            Booking.objects.create(
                hold=hold,
                user=self.user,
                zone=self.zone,
                starts_at=hold.starts_at,
                ends_at=hold.ends_at,
                unit_price_tiyin=hold.unit_price_tiyin,
                total_price_tiyin=hold.total_price_tiyin,
                status=Booking.Status.COMPLETED,
            )
        active_hold = self.make_hold()
        Booking.objects.create(
            hold=active_hold,
            user=self.user,
            zone=self.zone,
            starts_at=active_hold.starts_at,
            ends_at=active_hold.ends_at,
            unit_price_tiyin=active_hold.unit_price_tiyin,
            total_price_tiyin=active_hold.total_price_tiyin,
        )
        client = APIClient()
        client.force_authenticate(self.user)

        response = client.get("/api/v1/bookings/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(response.data["results"][0]["zone"]["name"], self.zone.name)
        self.assertEqual(
            response.data["results"][0]["zone"]["branch"]["club"]["name"],
            self.zone.branch.club.name,
        )


class BookingFixRegressionTests(TestCase):
    """Kod-tahlil davomida topilgan xatolarga regressiya testlari."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="fix_owner", phone="+998900000001")
        cls.customer = User.objects.create_user(username="fix_customer", phone="+998900000002")
        cls.other_owner = User.objects.create_user(username="fix_other", phone="+998900000003")
        cls.club = Club.objects.create(owner=cls.owner, name="Fix Club", status=Club.Status.ACTIVE)
        Club.objects.create(owner=cls.other_owner, name="Other Club", status=Club.Status.ACTIVE)
        city = City.objects.create(name="Fix City", slug="fix-city")
        cls.branch = Branch.objects.create(
            club=cls.club,
            city=city,
            name="Fix Branch",
            address="addr",
            latitude=41,
            longitude=69,
            status=Branch.Status.ACTIVE,
        )
        cls.zone = Zone.objects.create(
            branch=cls.branch,
            name="Fix Zone",
            capacity=5,
            price_per_hour_tiyin=2_000_000,
        )
        # PER_ZONE zona: booking_capacity == unit_count (2), lekin capacity == 10.
        cls.room = Zone.objects.create(
            branch=cls.branch,
            name="Fix Room",
            capacity=10,
            unit_count=2,
            booking_type=Zone.BookingType.PER_ZONE,
            price_per_hour_tiyin=3_000_000,
        )
        barber_user = User.objects.create_user(username="fix_barber", phone="+998900000004")
        cls.barber = Barber.objects.create(
            user=barber_user,
            club=cls.club,
            branch=cls.branch,
            full_name="Usta Aka",
            is_active=True,
        )

    def _make_customer_booking(self, status=Booking.Status.CONFIRMED):
        starts = timezone.now() + timedelta(days=1)
        return Booking.objects.create(
            user=self.customer,
            zone=self.zone,
            starts_at=starts,
            ends_at=starts + timedelta(hours=1),
            quantity=1,
            unit_price_tiyin=2_000_000,
            total_price_tiyin=2_000_000,
            status=status,
            confirmed_at=timezone.now() if status == Booking.Status.CONFIRMED else None,
        )

    def _future_working_datetime(self, hour=10):
        tz = ZoneInfo("Asia/Tashkent")
        moment = timezone.localtime(timezone.now(), tz) + timedelta(days=2)
        while moment.isoweekday() == 7:  # default ish kunlari 1-6 (yakshanba dam)
            moment += timedelta(days=1)
        return moment.replace(hour=hour, minute=0, second=0, microsecond=0)

    # Fix #1 — operator mijoz bronini bekor qila oladi
    def test_operator_can_cancel_customer_booking(self):
        booking = self._make_customer_booking()
        client = APIClient()
        client.force_authenticate(self.owner)
        response = client.post(
            f"/api/v1/cabinet/bookings/{booking.id}/cancel/",
            {"reason": "Klub yopiq"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertEqual(booking.cancellation.reason, "Klub yopiq")

    def test_foreign_operator_cannot_cancel_customer_booking(self):
        booking = self._make_customer_booking()
        client = APIClient()
        client.force_authenticate(self.other_owner)
        response = client.post(
            f"/api/v1/cabinet/bookings/{booking.id}/cancel/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    # Fix #2 — sartarosh broni validatsiyasi
    def test_barber_booking_rejects_past_time(self):
        client = APIClient()
        client.force_authenticate(self.customer)
        past = (timezone.now() - timedelta(hours=3)).isoformat()
        response = client.post(
            "/api/v1/bookings/barber/",
            {"barber_id": str(self.barber.id), "starts_at": past},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Booking.objects.filter(barber=self.barber).exists())

    def test_barber_booking_rejects_outside_working_hours(self):
        client = APIClient()
        client.force_authenticate(self.customer)
        moment = self._future_working_datetime(hour=3)  # 03:00 — ish vaqtidan tashqarida
        response = client.post(
            "/api/v1/bookings/barber/",
            {"barber_id": str(self.barber.id), "starts_at": moment.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_barber_booking_happy_path(self):
        client = APIClient()
        client.force_authenticate(self.customer)
        moment = self._future_working_datetime(hour=10)
        response = client.post(
            "/api/v1/bookings/barber/",
            {"barber_id": str(self.barber.id), "starts_at": moment.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], Booking.Status.CONFIRMED)

    # Fix #4 — availability PER_ZONE uchun booking_capacity qaytaradi
    def test_availability_capacity_uses_booking_capacity(self):
        tz = ZoneInfo("Asia/Tashkent")
        target_date = (timezone.localtime(timezone.now(), tz) + timedelta(days=1)).date()
        OperatingHour.objects.create(
            branch=self.branch,
            weekday=target_date.weekday(),
            opens_at="00:00",
            closes_at="23:59",
        )
        response = APIClient().get(
            f"/api/v1/branches/{self.branch.id}/availability/",
            {"date": target_date.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        room_data = next(z for z in response.data["zones"] if z["id"] == self.room.id)
        self.assertEqual(room_data["capacity"], self.room.booking_capacity)
        self.assertEqual(room_data["capacity"], 2)
