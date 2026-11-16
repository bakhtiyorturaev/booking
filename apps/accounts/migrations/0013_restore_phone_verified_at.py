from django.db import migrations, models


def backfill_phone_verified_at(apps, schema_editor):
    """Telegram orqali raqami bor foydalanuvchilarni tasdiqlangan deb belgilaydi.

    `0007_telegram_only_auth` maydonni o'chirib tashlagan, shuning uchun
    oldingi tasdiqlash vaqti saqlanmagan. Telegram bilan bog'langan va raqami
    mavjud foydalanuvchilar uchun `telegram_verified_at` eng yaqin haqiqatga
    mos qiymat — faqat shu holatda ko'chiramiz.
    """
    User = apps.get_model("accounts", "User")
    User.objects.filter(
        phone__isnull=False,
        telegram_verified_at__isnull=False,
        phone_verified_at__isnull=True,
    ).update(phone_verified_at=models.F("telegram_verified_at"))


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_localize_admin_model_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="phone_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_phone_verified_at, migrations.RunPython.noop),
    ]
