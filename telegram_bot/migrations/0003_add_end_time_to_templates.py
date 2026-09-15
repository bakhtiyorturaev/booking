from django.db import migrations


def add_end_time(apps, schema_editor):
    Template = apps.get_model("telegram_bot", "TelegramMessageTemplate")
    for template in Template.objects.filter(
        event__in=("PENDING", "CONFIRMED", "CANCELLED"),
        text__contains="Vaqt: {time}\n",
    ):
        template.text = template.text.replace(
            "Vaqt: {time}\n",
            "Vaqt: {time}–{end_time}\n",
        )
        template.save(update_fields=("text", "updated_at"))


class Migration(migrations.Migration):
    dependencies = [("telegram_bot", "0002_seed_message_templates")]
    operations = [migrations.RunPython(add_end_time, migrations.RunPython.noop)]
