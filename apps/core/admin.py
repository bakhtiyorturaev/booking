from django.contrib import admin
from apps.core.models import AppTranslation, SystemMessage


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