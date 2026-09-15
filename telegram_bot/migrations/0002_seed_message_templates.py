from django.db import migrations


TEMPLATES = {
    "PENDING": (
        "⏳ Yangi booking tasdiq kutmoqda.\n"
        "Booking: {booking_number}\nFilial: {branch}\nZona: {zone}\n"
        "Sana: {date}\nVaqt: {time}\nJoylar: {quantity}\n"
        "Mijoz: {customer}\nTelefon: {phone}"
    ),
    "CONFIRMED": (
        "✅ Yangi booking tasdiqlandi.\n"
        "Booking: {booking_number}\nFilial: {branch}\nZona: {zone}\n"
        "Sana: {date}\nVaqt: {time}\nJoylar: {quantity}\n"
        "Mijoz: {customer}\nTelefon: {phone}"
    ),
    "CANCELLED": (
        "❌ Booking bekor qilindi.\n"
        "Booking: {booking_number}\nFilial: {branch}\nZona: {zone}\n"
        "Sana: {date}\nVaqt: {time}\nSabab: {reason}"
    ),
}


def seed_templates(apps, schema_editor):
    Template = apps.get_model("telegram_bot", "TelegramMessageTemplate")
    for event, text in TEMPLATES.items():
        Template.objects.get_or_create(event=event, defaults={"text": text})


class Migration(migrations.Migration):
    dependencies = [("telegram_bot", "0001_initial")]
    operations = [migrations.RunPython(seed_templates, migrations.RunPython.noop)]
