from django.contrib import admin

from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "rating", "is_visible", "created_at")
    list_filter = ("rating", "is_visible", "club")
    search_fields = ("user__username", "club__name", "comment")
    readonly_fields = ("booking", "user", "club", "created_at", "updated_at")
