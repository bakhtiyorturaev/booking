from django.core.management.base import BaseCommand

from apps.bookings.services import process_booking_lifecycle


class Command(BaseCommand):
    help = "Auto-confirm va no-show qoidalarini bir marta bajaradi."

    def handle(self, *args, **options):
        result = process_booking_lifecycle()
        self.stdout.write(
            f"confirmed={result['confirmed']} no_shows={result['no_shows']}"
        )
