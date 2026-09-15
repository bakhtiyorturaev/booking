from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "actor",
        "method",
        "path",
        "status_code",
        "ip_address",
    )
    list_filter = ("method", "status_code", "created_at")
    search_fields = ("actor__username", "path", "action", "object_id", "request_id")
    readonly_fields = (
        "id",
        "actor",
        "method",
        "path",
        "action",
        "object_id",
        "status_code",
        "ip_address",
        "user_agent",
        "request_id",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
