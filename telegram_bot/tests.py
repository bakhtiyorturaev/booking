from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Booking, BookingHold
from apps.clubs.models import Branch, City, Club, Zone
from telegram_bot.client import TelegramClient
from telegram_bot.models import (
    BranchTelegramBinding,
    TelegramBotSettings,
    TelegramBookingMessage,
    TelegramGroup,
)
from telegram_bot.services import (
    cancel_booking_from_telegram,
    confirm_booking,
    dispatch_pending_messages,
    process_confirmation_timeouts,
    queue_booking_message,
    render_booking_message,
)


class FakeTelegramClient:
    def send_message(self, chat_id, text, reply_markup=None, *args, **kwargs):
        return {"message_id": 101}

    def edit_message(self, chat_id, message_id, text, reply_markup=None):
        return True


class TelegramClientSettingsTests(TestCase):
    @patch("telegram_bot.client.requests.post")
    def test_client_uses_database_token_and_timeout(self, post):
        response = Mock()
        response.json.return_value = {"ok": True, "result": {"id": 1}}
        post.return_value = response
        TelegramBotSettings.objects.update_or_create(
            pk=1,
            defaults={
                "is_enabled": True,
                "bot_token": "database-token",
                "request_timeout_seconds": 9,
            },
        )

        TelegramClient().request("getMe")

        self.assertIn("database-token", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["timeout"], 9)


class TelegramBookingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="telegram_user", phone="+998901112233")
        club = Club.objects.create(owner=cls.user, name="Club", status=Club.Status.ACTIVE)
        city = City.objects.create(name="City", slug="telegram-city")
        cls.branch = Branch.objects.create(
            club=club,
            city=city,
            name="Branch",
            address="Address",
            latitude=41,
            longitude=69,
            status=Branch.Status.ACTIVE,
        )
        cls.zone = Zone.objects.create(
            branch=cls.branch,
            name="Zone",
            capacity=5,
            price_per_hour_tiyin=100_000,
        )
        cls.group = TelegramGroup.objects.create(name="Group", chat_id=-1009876543210)
        BranchTelegramBinding.objects.create(branch=cls.branch, group=cls.group)

    def make_booking(self):
        starts_at = timezone.now() + timedelta(days=1)
        hold = BookingHold.objects.create(
            user=self.user,
            zone=self.zone,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            unit_price_tiyin=100_000,
            total_price_tiyin=100_000,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        return Booking.objects.create(
            hold=hold,
            user=self.user,
            zone=self.zone,
            starts_at=hold.starts_at,
            ends_at=hold.ends_at,
            unit_price_tiyin=hold.unit_price_tiyin,
            total_price_tiyin=hold.total_price_tiyin,
        )

    def test_one_group_can_have_multiple_branches(self):
        second = Branch.objects.create(
            club=self.branch.club,
            city=self.branch.city,
            name="Second",
            address="Address",
            latitude=41,
            longitude=69,
        )
        BranchTelegramBinding.objects.create(branch=second, group=self.group)

        self.assertEqual(self.group.branch_bindings.count(), 2)

    def test_confirm_callback_service_confirms_booking(self):
        booking = self.make_booking()
        queue_booking_message(booking)

        confirm_booking(booking.id, 123, "admin")

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    def test_cancel_callback_service_saves_reason(self):
        booking = self.make_booking()
        queue_booking_message(booking)

        cancel_booking_from_telegram(booking.id, "technical", 123, "admin")

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertEqual(booking.cancellation.source, "TELEGRAM")
        self.assertTrue(booking.cancellation.reason)

    def test_pending_message_is_sent(self):
        booking = self.make_booking()
        message = queue_booking_message(booking)

        dispatch_pending_messages(FakeTelegramClient())

        message.refresh_from_db()
        self.assertEqual(message.status, TelegramBookingMessage.Status.SENT)
        self.assertEqual(message.message_id, 101)

    def test_message_contains_start_and_end_time(self):
        text = render_booking_message(self.make_booking())

        self.assertIn("–", text)

    def test_pending_booking_is_automatically_confirmed_after_timeout(self):
        booking = self.make_booking()
        queue_booking_message(booking)
        TelegramBotSettings.objects.update_or_create(
            pk=1,
            defaults={
                "auto_confirm_enabled": True,
                "confirmation_timeout_minutes": 5,
            },
        )
        Booking.objects.filter(pk=booking.pk).update(
            created_at=timezone.now() - timedelta(minutes=6)
        )

        self.assertEqual(process_confirmation_timeouts(), 1)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)

    def test_auto_confirmation_can_be_disabled(self):
        booking = self.make_booking()
        TelegramBotSettings.objects.update_or_create(
            pk=1,
            defaults={
                "auto_confirm_enabled": False,
                "confirmation_timeout_minutes": 5,
            },
        )
        Booking.objects.filter(pk=booking.pk).update(
            created_at=timezone.now() - timedelta(minutes=6)
        )

        self.assertEqual(process_confirmation_timeouts(), 0)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PENDING_CONFIRMATION)

    def test_send_customer_booking_notification_zone(self):
        booking = self.make_booking()
        self.user.profile.telegram_chat_id = "12345678"
        self.user.profile.save()

        fake_client = Mock()
        from telegram_bot.services import send_customer_booking_notification
        send_customer_booking_notification(booking, Booking.Status.CONFIRMED, client=fake_client)

        self.assertTrue(fake_client.send_message.called)
        call_args = fake_client.send_message.call_args
        self.assertEqual(call_args.kwargs["chat_id"], "12345678")
        self.assertIn("tasdiqlandi", call_args.kwargs["text"])
        self.assertIn(booking.booking_number, call_args.kwargs["text"])

    def test_send_customer_booking_notification_barber(self):
        from apps.barbers.models import Barber
        barber_user = User.objects.create_user(username="barber_u", phone="+998909998877")
        barber = Barber.objects.create(
            user=barber_user,
            full_name="Master Rustam",
            phone="+998909998877",
            club=self.branch.club,
            branch=self.branch,
        )
        booking = Booking.objects.create(
            user=self.user,
            barber=barber,
            starts_at=timezone.now() + timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=1, hours=1),
            quantity=1,
            unit_price_tiyin=0,
            total_price_tiyin=0,
            status=Booking.Status.CONFIRMED,
        )
        self.user.profile.telegram_chat_id = "87654321"
        self.user.profile.save()

        fake_client = Mock()
        from telegram_bot.services import send_customer_booking_notification
        send_customer_booking_notification(booking, Booking.Status.CONFIRMED, client=fake_client)

        self.assertTrue(fake_client.send_message.called)
        call_args = fake_client.send_message.call_args
        self.assertEqual(call_args.kwargs["chat_id"], "87654321")
        self.assertIn("Master Rustam", call_args.kwargs["text"])
        self.assertIn(booking.booking_number, call_args.kwargs["text"])

