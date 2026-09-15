from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_add_otp_phone_created_index")]

    operations = [
        migrations.AddField(model_name="user", name="telegram_user_id", field=models.BigIntegerField(blank=True, null=True, unique=True)),
        migrations.AddField(model_name="user", name="telegram_verified_at", field=models.DateTimeField(blank=True, null=True)),
    ]
