from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clubs", "0015_set_cancellation_window_to_one_hour"),
    ]

    operations = [
        migrations.AddField(
            model_name="zone",
            name="booking_type",
            field=models.CharField(
                choices=[
                    ("PER_SEAT", "Har bir joy uchun"),
                    ("PER_ZONE", "Butun xona uchun"),
                ],
                default="PER_SEAT",
                help_text="Narx har bir joy yoki butun xona uchun hisoblanishi.",
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="zone",
            name="unit_count",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Bir xil xonalar soni. Joy bo‘yicha bronlashda 1.",
                validators=[MinValueValidator(1), MaxValueValidator(500)],
            ),
        ),
        migrations.AlterField(
            model_name="zone",
            name="capacity",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Zaldagi joylar yoki bitta xonaning odam sig‘imi.",
                validators=[MinValueValidator(1), MaxValueValidator(500)],
            ),
        ),
        migrations.AlterField(
            model_name="zone",
            name="price_per_hour_tiyin",
            field=models.PositiveBigIntegerField(
                help_text="Bitta joy yoki xonaning bir soatlik narxi, tiyinlarda.",
                validators=[MinValueValidator(0)],
            ),
        ),
    ]
