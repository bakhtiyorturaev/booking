from django.db import migrations, models
from django.db.models import Min
from django.core.validators import MinValueValidator


def copy_tariff_prices_to_zones(apps, schema_editor):
    Zone = apps.get_model("clubs", "Zone")
    Tariff = apps.get_model("clubs", "Tariff")

    for zone in Zone.objects.all().iterator():
        tariffs = Tariff.objects.filter(zone_id=zone.pk)
        price = tariffs.filter(is_active=True).aggregate(
            value=Min("price_per_hour_tiyin")
        )["value"]
        if price is None:
            price = tariffs.aggregate(value=Min("price_per_hour_tiyin"))["value"]
        Zone.objects.filter(pk=zone.pk).update(
            price_per_hour_tiyin=price if price is not None else 0
        )


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0009_use_image_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="zone",
            name="price_per_hour_tiyin",
            field=models.PositiveBigIntegerField(
                default=0,
                help_text="Bitta joyning bir soatlik narxi, tiyinlarda.",
                validators=[MinValueValidator(0)],
            ),
            preserve_default=False,
        ),
        migrations.RunPython(
            copy_tariff_prices_to_zones,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.DeleteModel(
            name="Tariff",
        ),
    ]
