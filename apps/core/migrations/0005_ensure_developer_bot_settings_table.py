from django.db import migrations


def ensure_developer_bot_settings_table(apps, schema_editor):
    # Older installations already have this table; fresh ones no longer install
    # the former developer_bot app that originally created it.
    connection = schema_editor.connection
    model = apps.get_model("core", "DeveloperBotSettings")
    if model._meta.db_table not in connection.introspection.table_names():
        schema_editor.create_model(model)
    model.objects.using(connection.alias).get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_servicetype"),
    ]

    operations = [
        migrations.RunPython(ensure_developer_bot_settings_table, migrations.RunPython.noop),
    ]
