from django.db import migrations, models


SPECIFICATION_KEYS = ("cpu", "gpu", "ram", "monitor")


def combine_computer_specifications(apps, schema_editor):
    Zone = apps.get_model("clubs", "Zone")
    for zone in Zone.objects.order_by().iterator():
        specifications = dict(zone.peripherals or {})
        for key in SPECIFICATION_KEYS:
            value = getattr(zone, key)
            if value:
                specifications[key] = value
        zone.specifications = specifications
        zone.save(update_fields=["specifications"])


def restore_computer_fields(apps, schema_editor):
    Zone = apps.get_model("clubs", "Zone")
    for zone in Zone.objects.order_by().iterator():
        specifications = dict(zone.specifications or {})
        for key in SPECIFICATION_KEYS:
            setattr(zone, key, specifications.pop(key, ""))
        zone.peripherals = specifications
        zone.save(
            update_fields=[
                "cpu",
                "gpu",
                "ram",
                "monitor",
                "peripherals",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("clubs", "0004_tariff_price_in_tiyin"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="zone",
            name="zone_branch_status_idx",
        ),
        migrations.AddField(
            model_name="zone",
            name="resource_type",
            field=models.CharField(
                choices=[
                    ("COMPUTER", "Computer"),
                    ("PLAYSTATION", "PlayStation"),
                ],
                default="COMPUTER",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="zone",
            name="specifications",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(
            combine_computer_specifications,
            reverse_code=restore_computer_fields,
        ),
        migrations.RemoveField(
            model_name="branch",
            name="amenities",
        ),
        migrations.RemoveField(model_name="zone", name="cpu"),
        migrations.RemoveField(model_name="zone", name="gpu"),
        migrations.RemoveField(model_name="zone", name="ram"),
        migrations.RemoveField(model_name="zone", name="monitor"),
        migrations.RemoveField(model_name="zone", name="peripherals"),
        migrations.DeleteModel(name="Amenity"),
        migrations.AddIndex(
            model_name="zone",
            index=models.Index(
                fields=["branch", "resource_type", "status"],
                name="zone_branch_type_status_idx",
            ),
        ),
    ]
