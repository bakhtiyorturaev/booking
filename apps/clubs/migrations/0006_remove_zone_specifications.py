from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("clubs", "0005_zone_service_types"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="zone",
            name="specifications",
        ),
    ]
