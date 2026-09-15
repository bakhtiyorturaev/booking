import hashlib
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Booking, BookingHold, Cancellation
from apps.clubs.models import Zone
from apps.payments.models import UserSubscription


SCENARIOS = (
    ("completed", Booking.Status.COMPLETED, -5, 16, 2),
    ("cancelled", Booking.Status.CANCELLED, -3, 20, 1),
    ("no_show", Booking.Status.NO_SHOW, -1, 22, 1),
    ("confirmed", Booking.Status.CONFIRMED, 1, 18, 1),
)


class Command(BaseCommand):
    help = "Frontend ko‘rinishini tekshirish uchun demo bronlar yaratadi."

    def add_arguments(self, parser):
        parser.add_argument("--phone", default="+998123456789")

    @transaction.atomic
    def handle(self, *args, **options):
        phone = options["phone"]
        user = User.objects.filter(phone=phone, role=User.Role.CUSTOMER).first()
        zones = list(
            Zone.objects.filter(
                status=Zone.Status.ACTIVE,
                branch__status="ACTIVE",
                branch__club__status="ACTIVE",
            ).select_related("branch")
        )
        if user is None or not zones:
            raise CommandError("Faol mijoz va kamida bitta faol zona kerak.")

        subscription, _ = UserSubscription.objects.get_or_create(user=user)
        subscription.activate()

        now = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        prefix = int(hashlib.sha256(phone.encode()).hexdigest()[:8], 16) % 100_000_000

        for index, (key, status, day_offset, hour, quantity) in enumerate(SCENARIOS, 1):
            zone = (
                next(
                    (item for item in zones if item.booking_type == Zone.BookingType.PER_ZONE),
                    zones[0],
                )
                if key == "confirmed"
                else zones[(index - 1) % len(zones)]
            )
            starts_at = (now + timedelta(days=day_offset)).replace(hour=hour)
            ends_at = starts_at + timedelta(hours=2)
            quantity = min(quantity, zone.booking_capacity)
            total = zone.price_per_hour_tiyin * 2 * quantity
            booking_number = f"{prefix:08d}{index:04d}"
            booking = Booking.objects.filter(booking_number=booking_number).first()

            if booking is None:
                hold = BookingHold.objects.create(
                    user=user,
                    zone=zone,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    quantity=quantity,
                    unit_price_tiyin=zone.price_per_hour_tiyin,
                    total_price_tiyin=total,
                    status=BookingHold.Status.CONVERTED,
                    expires_at=now,
                )
                booking = Booking(hold=hold, booking_number=booking_number)
            else:
                hold = booking.hold
                hold.zone = zone
                hold.starts_at = starts_at
                hold.ends_at = ends_at
                hold.quantity = quantity
                hold.unit_price_tiyin = zone.price_per_hour_tiyin
                hold.total_price_tiyin = total
                hold.status = BookingHold.Status.CONVERTED
                hold.expires_at = now
                hold.save()

            booking.user = user
            booking.zone = zone
            booking.starts_at = starts_at
            booking.ends_at = ends_at
            booking.quantity = quantity
            booking.unit_price_tiyin = zone.price_per_hour_tiyin
            booking.total_price_tiyin = total
            booking.status = status
            booking.save()

            if key == "cancelled":
                Cancellation.objects.update_or_create(
                    booking=booking,
                    defaults={
                        "requested_by": user,
                        "source": Cancellation.Source.USER,
                        "reason": "Test uchun bekor qilingan bron",
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"{phone} uchun {len(SCENARIOS)} ta demo bron va 30 kunlik Paid obuna tayyor."
            )
        )
