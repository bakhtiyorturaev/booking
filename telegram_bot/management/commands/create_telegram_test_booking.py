from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.bookings.models import Booking
from apps.bookings.services import create_booking, create_hold
from apps.clubs.models import Branch, City, Club, Zone
from apps.payments.models import UserSubscription
from telegram_bot.client import TelegramClient
from telegram_bot.models import (
    BranchTelegramBinding,
    TelegramBotSettings,
    TelegramGroup,
)
from telegram_bot.services import dispatch_pending_messages, queue_booking_message


class Command(BaseCommand):
    help = "Telegram tugmalarini tekshirish uchun pending booking yaratadi."

    def handle(self, *args, **options):
        configuration = TelegramBotSettings.objects.filter(pk=1).first()
        chat_id = configuration.test_group_chat_id if configuration else None
        group = TelegramGroup.objects.filter(chat_id=chat_id, is_active=True).first()
        if not group:
            raise CommandError("Avval check_telegram_bot buyrug‘ini bajaring.")

        user, _ = get_user_model().objects.get_or_create(
            username="telegram_test_customer",
            defaults={"phone": "+998900000001"},
        )
        subscription, _ = UserSubscription.objects.get_or_create(user=user)
        subscription.activate()
        city, _ = City.objects.get_or_create(
            slug="telegram-test-city",
            defaults={"name": "Telegram Test City"},
        )
        club, _ = Club.objects.get_or_create(
            slug="telegram-test-club",
            defaults={"owner": user, "name": "Telegram Test Club"},
        )
        club.status = Club.Status.ACTIVE
        club.save(update_fields=("status", "updated_at"))
        branch, _ = Branch.objects.get_or_create(
            club=club,
            name="Telegram Test Branch",
            defaults={
                "city": city,
                "address": "Test address",
                "latitude": Decimal("41.311081"),
                "longitude": Decimal("69.240562"),
            },
        )
        branch.status = Branch.Status.ACTIVE
        branch.is_24_hours = True
        branch.save(update_fields=("status", "is_24_hours", "updated_at"))
        zone, _ = Zone.objects.get_or_create(
            branch=branch,
            name="Test Zone",
            defaults={"capacity": 5, "price_per_hour_tiyin": 1_000_000},
        )
        BranchTelegramBinding.objects.update_or_create(
            branch=branch,
            defaults={"group": group, "is_active": True},
        )

        booking = Booking.objects.filter(
            user=user,
            status=Booking.Status.PENDING_CONFIRMATION,
            ends_at__gt=timezone.now(),
        ).first()
        if not booking:
            local_now = timezone.localtime(timezone.now(), ZoneInfo(branch.timezone))
            starts_at = (local_now + timedelta(days=1)).replace(
                minute=0,
                second=0,
                microsecond=0,
            )
            hold = create_hold(
                user,
                zone.id,
                starts_at,
                starts_at + timedelta(hours=1),
            )
            booking = create_booking(user, hold.id)
        else:
            queue_booking_message(booking)

        dispatch_pending_messages(TelegramClient())
        self.stdout.write(
            self.style.SUCCESS(
                f"Booking {booking.booking_number} guruhga yuborildi: {branch.name}"
            )
        )
