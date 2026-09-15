from decimal import Decimal

import django.core.validators
from django.db import migrations, models


def convert_uzs_to_tiyin(apps, schema_editor):
    Tariff = apps.get_model("clubs", "Tariff")
    for tariff in Tariff.objects.order_by().iterator():
        tariff.price_per_hour_tiyin = int(
            Decimal(tariff.price_per_hour_tiyin) * 100
        )
        tariff.save(update_fields=["price_per_hour_tiyin"])


def convert_tiyin_to_uzs(apps, schema_editor):
    Tariff = apps.get_model("clubs", "Tariff")
    for tariff in Tariff.objects.order_by().iterator():
        tariff.price_per_hour_tiyin = (
            Decimal(tariff.price_per_hour_tiyin) / 100
        )
        tariff.save(update_fields=["price_per_hour_tiyin"])


class Migration(migrations.Migration):
    dependencies = [
        ("clubs", "0003_remove_computer_computer_zone_status_idx_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="tariff",
            old_name="price_per_hour",
            new_name="price_per_hour_tiyin",
        ),
        migrations.RunPython(
            convert_uzs_to_tiyin,
            reverse_code=convert_tiyin_to_uzs,
        ),
        migrations.AlterField(
            model_name="tariff",
            name="price_per_hour_tiyin",
            field=models.PositiveBigIntegerField(
                help_text="Hourly price in tiyin (1 UZS = 100 tiyin).",
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AlterModelOptions(
            name="tariff",
            options={"ordering": ("price_per_hour_tiyin", "name")},
        ),
    ]
