from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import (
    User,
    UserProfile,
    UserSession,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-created_at",)

    list_display = (
        "username",
        "phone",
        "telegram_user_id",
        "role",
        "status",
        "is_staff",
        "telegram_verified_at",
        "created_at",
    )
    list_filter = (
        "role",
        "status",
        "is_staff",
        "is_superuser",
    )
    search_fields = (
        "username",
        "phone",
        "telegram_user_id",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "phone",
                    "password",
                )
            },
        ),
        (
            "Telegram & Status",
            {
                "fields": (
                    "telegram_user_id",
                    "telegram_verified_at",
                    "role",
                    "status",
                    "last_login",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "preferred_language",
        "city",
        "profile_completed_at",
    )
    search_fields = (
        "user__username",
        "user__phone",
        "full_name",
        "city",
    )
    list_filter = (
        "preferred_language",
        "telegram_notifications_enabled",
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "device_name",
        "ip_address",
        "expires_at",
        "revoked_at",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__phone",
        "device_name",
        "ip_address",
    )
    list_filter = (
        "created_at",
        "expires_at",
        "revoked_at",
    )
    readonly_fields = (
        "refresh_token_hash",
        "created_at",
    )
