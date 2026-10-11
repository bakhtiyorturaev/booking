from django.contrib import admin
from apps.core.admin_forms import SecretSettingsForm
from apps.core.models import AppTranslation, City, DeveloperBotSettings, District, ServiceType, SystemMessage


@admin.register(AppTranslation)
class AppTranslationAdmin(admin.ModelAdmin):
    list_display = ("code", "text_uz", "is_active", "updated_at",)
    list_filter = ("is_active",)
    search_fields = ("code", "text_uz", "text_ru", "text_en",)
    ordering = ("code", "text_uz",)


@admin.register(SystemMessage)
class SystemMessageAdmin(admin.ModelAdmin):
    list_display = ("code", "text_uz", "is_active", "updated_at",)
    list_filter = ("is_active",)
    search_fields = ("code", "text_uz", "text_ru", "text_en",)
    ordering = ("code","text_uz",)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "slug", "is_active", "sort_order")
    list_filter = ("is_active", "city")
    search_fields = ("name", "slug", "city__name")
    autocomplete_fields = ("city",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "sort_order")
    search_fields = ("name", "code")

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


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
