from django.apps import AppConfig


class DeveloperBotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.developer_bot"
    verbose_name = "Developer Telegram bot"

    def ready(self):
        from apps.developer_bot import signals  # noqa: F401
