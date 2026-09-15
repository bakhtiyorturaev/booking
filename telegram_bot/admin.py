from django.contrib import admin

from apps.core.admin_forms import SecretSettingsForm
from telegram_bot.models import (
    BranchTelegramBinding,
    TelegramBotSettings,
    TelegramBookingMessage,
    TelegramCancellationReason,
    TelegramGroup,
    TelegramMessageTemplate,
)


class TelegramBotSettingsForm(SecretSettingsForm):
    class Meta:
        model = TelegramBotSettings
        fields = "__all__"


@admin.register(TelegramGroup)
class TelegramGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "chat_id", "language", "is_active")
    list_filter = ("language", "is_active")
    search_fields = ("name", "chat_id")


@admin.register(BranchTelegramBinding)
class BranchTelegramBindingAdmin(admin.ModelAdmin):
    list_display = ("branch", "group", "is_active")
    list_filter = ("is_active", "group")
    search_fields = ("branch__name", "group__name")


@admin.register(TelegramMessageTemplate)
class TelegramMessageTemplateAdmin(admin.ModelAdmin):
    list_display = ("event", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(TelegramBotSettings)
class TelegramBotSettingsAdmin(admin.ModelAdmin):
    form = TelegramBotSettingsForm
    list_display = (
        "is_enabled",
        "is_configured",
        "auto_confirm_enabled",
        "confirmation_timeout_minutes",
        "updated_at",
    )
    fieldsets = (
        ("Ulanish", {
            "fields": (
                "is_enabled",
                "bot_token",
                "login_client_id",
                "login_client_secret",
                "test_group_chat_id",
                "request_timeout_seconds",
                "polling_timeout_seconds",
                "retry_delay_seconds",
            ),
        }),
        ("Bronlarni tasdiqlash", {
            "fields": (
                "auto_confirm_enabled",
                "confirmation_timeout_minutes",
            ),
        }),
    )

    def has_add_permission(self, request):
        return not TelegramBotSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TelegramCancellationReason)
class TelegramCancellationReasonAdmin(admin.ModelAdmin):
    list_display = ("code", "title_uz", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "title_uz", "title_ru", "title_en")


@admin.register(TelegramBookingMessage)
class TelegramBookingMessageAdmin(admin.ModelAdmin):
    list_display = ("booking", "group", "operation", "status", "attempts")
    list_filter = ("status", "operation", "group")
    search_fields = ("booking__booking_number", "acted_by_name")
    readonly_fields = (
        "message_id",
        "attempts",
        "last_error",
        "acted_by_telegram_id",
        "acted_by_name",
        "acted_at",
    )
