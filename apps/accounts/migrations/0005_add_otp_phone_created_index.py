from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_add_password_otp_purposes")]

    operations = [
        migrations.AddIndex(
            model_name="otprequest",
            index=models.Index(
                fields=["phone", "created_at"],
                name="otp_phone_created_idx",
            ),
        ),
    ]
