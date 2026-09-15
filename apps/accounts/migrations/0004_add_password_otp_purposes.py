from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_alter_user_role")]

    operations = [
        migrations.AlterField(
            model_name="otprequest",
            name="purpose",
            field=models.CharField(
                choices=[
                    ("LOGIN", "Login"),
                    ("REGISTER", "Register"),
                    ("PASSWORD_RESET", "Password reset"),
                    ("PHONE_CHANGE", "Phone change"),
                ],
                default="LOGIN",
                max_length=20,
            ),
        ),
    ]
