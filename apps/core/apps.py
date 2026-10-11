from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'apps.core'
    verbose_name = "Tizim sozlamalari"

    def ready(self):
        from apps.core import checks  # noqa: F401
        from apps.core.developer_bot import signals  # noqa: F401
