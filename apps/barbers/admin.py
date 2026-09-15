from django.contrib import admin
from apps.barbers.models import Barber


@admin.register(Barber)
class BarberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "club", "branch", "status", "affiliation_status", "rating", "is_active")
    list_filter = ("status", "affiliation_status", "is_active", "club")
    search_fields = ("full_name", "phone", "user__username")
    readonly_fields = ("rating", "review_count", "created_at", "updated_at")
