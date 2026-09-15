import django.core.validators
from django.db import migrations, models


TEMPLATE_TRANSLATIONS = {
    "PENDING": {
        "ru": (
            "⏳ Новое бронирование ожидает подтверждения.\n"
            "Бронирование: {booking_number}\nФилиал: {branch}\nЗона: {zone}\n"
            "Дата: {date}\nВремя: {time}–{end_time}\nМеста: {quantity}\n"
            "Клиент: {customer}\nТелефон: {phone}"
        ),
        "en": (
            "⏳ A new booking is awaiting confirmation.\n"
            "Booking: {booking_number}\nBranch: {branch}\nZone: {zone}\n"
            "Date: {date}\nTime: {time}–{end_time}\nPlaces: {quantity}\n"
            "Customer: {customer}\nPhone: {phone}"
        ),
    },
    "CONFIRMED": {
        "ru": (
            "✅ Новое бронирование подтверждено.\n"
            "Бронирование: {booking_number}\nФилиал: {branch}\nЗона: {zone}\n"
            "Дата: {date}\nВремя: {time}–{end_time}\nМеста: {quantity}\n"
            "Клиент: {customer}\nТелефон: {phone}"
        ),
        "en": (
            "✅ A new booking was confirmed.\n"
            "Booking: {booking_number}\nBranch: {branch}\nZone: {zone}\n"
            "Date: {date}\nTime: {time}–{end_time}\nPlaces: {quantity}\n"
            "Customer: {customer}\nPhone: {phone}"
        ),
    },
    "CANCELLED": {
        "ru": (
            "❌ Бронирование отменено.\nБронирование: {booking_number}\n"
            "Филиал: {branch}\nЗона: {zone}\nДата: {date}\n"
            "Время: {time}–{end_time}\nПричина: {reason}"
        ),
        "en": (
            "❌ Booking cancelled.\nBooking: {booking_number}\nBranch: {branch}\n"
            "Zone: {zone}\nDate: {date}\nTime: {time}–{end_time}\n"
            "Reason: {reason}"
        ),
    },
}


REASONS = (
    {
        "code": "closed",
        "title_uz": "Filial yopiq",
        "title_ru": "Филиал закрыт",
        "title_en": "Branch closed",
        "reason_uz": "Filial vaqtincha yopiq.",
        "reason_ru": "Филиал временно закрыт.",
        "reason_en": "The branch is temporarily closed.",
        "sort_order": 10,
    },
    {
        "code": "technical",
        "title_uz": "Texnik nosozlik",
        "title_ru": "Техническая неисправность",
        "title_en": "Technical issue",
        "reason_uz": "Texnik nosozlik yuz berdi.",
        "reason_ru": "Возникла техническая неисправность.",
        "reason_en": "A technical issue occurred.",
        "sort_order": 20,
    },
    {
        "code": "unavailable",
        "title_uz": "Joy mavjud emas",
        "title_ru": "Место недоступно",
        "title_en": "Place unavailable",
        "reason_uz": "Tanlangan joy mavjud emas.",
        "reason_ru": "Выбранное место недоступно.",
        "reason_en": "The selected place is unavailable.",
        "sort_order": 30,
    },
)


def seed_dynamic_data(apps, schema_editor):
    Template = apps.get_model("telegram_bot", "TelegramMessageTemplate")
    Reason = apps.get_model("telegram_bot", "TelegramCancellationReason")
    Settings = apps.get_model("telegram_bot", "TelegramBotSettings")
    for event, translations in TEMPLATE_TRANSLATIONS.items():
        Template.objects.filter(event=event).update(
            text_ru=translations["ru"],
            text_en=translations["en"],
        )
    for reason in REASONS:
        Reason.objects.get_or_create(code=reason["code"], defaults=reason)
    Settings.objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [("telegram_bot", "0003_add_end_time_to_templates")]
    operations = [
        migrations.AddField(
            model_name="telegramgroup",
            name="language",
            field=models.CharField(
                choices=[("uz", "O‘zbek"), ("ru", "Русский"), ("en", "English")],
                default="uz",
                max_length=2,
            ),
        ),
        migrations.RenameField(
            model_name="telegrammessagetemplate",
            old_name="text",
            new_name="text_uz",
        ),
        migrations.AddField(
            model_name="telegrammessagetemplate",
            name="text_ru",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="telegrammessagetemplate",
            name="text_en",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="TelegramBotSettings",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False),
                ),
                ("auto_confirm_enabled", models.BooleanField(default=True)),
                (
                    "confirmation_timeout_minutes",
                    models.PositiveSmallIntegerField(
                        default=5,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(1440),
                        ],
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "telegram_bot_settings",
                "verbose_name_plural": "Telegram bot settings",
            },
        ),
        migrations.CreateModel(
            name="TelegramCancellationReason",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=20, unique=True)),
                ("title_uz", models.CharField(max_length=100)),
                ("title_ru", models.CharField(max_length=100)),
                ("title_en", models.CharField(max_length=100)),
                ("reason_uz", models.CharField(max_length=500)),
                ("reason_ru", models.CharField(max_length=500)),
                ("reason_en", models.CharField(max_length=500)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "telegram_cancellation_reasons",
                "ordering": ("sort_order", "code"),
            },
        ),
        migrations.RunPython(seed_dynamic_data, migrations.RunPython.noop),
    ]
