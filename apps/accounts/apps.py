from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'apps.accounts'
    verbose_name = "Foydalanuvchilar"

    def ready(self):
        # drf-spectacular custom authentication extensionini ro'yxatdan o'tkazadi.
        from apps.accounts import schema  # noqa: F401
