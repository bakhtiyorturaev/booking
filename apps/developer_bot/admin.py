from django.contrib import admin

from apps.core.admin_forms import SecretSettingsForm
from apps.developer_bot.models import DeveloperBotSettings


class DeveloperBotSettingsForm(SecretSettingsForm):
    class Meta:
        model = DeveloperBotSettings
        fields = "__all__"


@admin.register(DeveloperBotSettings)
class DeveloperBotSettingsAdmin(admin.ModelAdmin):
    form = DeveloperBotSettingsForm
    list_display = (
        "is_enabled",
        "is_configured",
        "environment",
        "notify_errors",
        "updated_at",
    )
    fieldsets = (
        ("Ulanish", {
            "fields": (
                "is_enabled",
                "bot_token",
                "chat_id",
                "environment",
                "request_timeout_seconds",
            ),
        }),
        ("Bildirishnomalar", {
            "fields": (
                "notify_errors",
                "notify_user_events",
                "notify_booking_events",
            ),
        }),
    )

    def has_add_permission(self, request):
        return not DeveloperBotSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
