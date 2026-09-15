from django.db import migrations


def create_settings(apps, schema_editor):
    DeveloperBotSettings = apps.get_model(
        "developer_bot", "DeveloperBotSettings"
    )
    DeveloperBotSettings.objects.get_or_create(pk=1)


def remove_settings(apps, schema_editor):
    DeveloperBotSettings = apps.get_model(
        "developer_bot", "DeveloperBotSettings"
    )
    DeveloperBotSettings.objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("developer_bot", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_settings, remove_settings),
    ]

