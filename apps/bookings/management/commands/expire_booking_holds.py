from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bookings.models import BookingHold


class Command(BaseCommand):
    help = "Muddati tugagan booking holdlarni expired holatiga o‘tkazadi."

    def handle(self, *args, **options):
        updated = BookingHold.objects.filter(
            status=BookingHold.Status.HELD,
            expires_at__lte=timezone.now(),
        ).update(status=BookingHold.Status.EXPIRED, updated_at=timezone.now())
        self.stdout.write(self.style.SUCCESS(f"{updated} ta hold yangilandi."))
