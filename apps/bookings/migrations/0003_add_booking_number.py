import secrets

import apps.bookings.models
from django.db import migrations, models


def populate_booking_numbers(apps, schema_editor):
    Booking = apps.get_model("bookings", "Booking")
    used = set(
        Booking.objects.exclude(booking_number__isnull=True).values_list(
            "booking_number",
            flat=True,
        )
    )
    for booking in Booking.objects.filter(booking_number__isnull=True).iterator():
        while True:
            number = str(secrets.randbelow(900_000_000_000) + 100_000_000_000)
            if number not in used:
                break
        booking.booking_number = number
        booking.save(update_fields=("booking_number",))
        used.add(number)


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0002_make_bookings_payment_free"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="booking_number",
            field=models.CharField(max_length=12, null=True, editable=False),
        ),
        migrations.RunPython(
            populate_booking_numbers,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="booking",
            name="booking_number",
            field=models.CharField(
                max_length=12,
                unique=True,
                editable=False,
                default=apps.bookings.models.generate_booking_number,
            ),
        ),
    ]
