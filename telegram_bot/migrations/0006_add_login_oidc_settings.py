from django.db import migrations, models

import apps.core.fields


class Migration(migrations.Migration):
    dependencies = [("telegram_bot", "0005_telegrambotsettings_bot_token_and_more")]

    operations = [
        migrations.AddField(model_name="telegrambotsettings", name="login_client_id", field=models.BigIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="telegrambotsettings", name="login_client_secret", field=apps.core.fields.EncryptedTextField(blank=True)),
    ]
