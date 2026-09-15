from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'apps.accounts'

    def ready(self):
        # drf-spectacular custom authentication extensionini ro'yxatdan o'tkazadi.
        from apps.accounts import schema  # noqa: F401
