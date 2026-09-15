from django.contrib import admin

from apps.clubs.models import (
    Branch,
    BranchImage,
    City,
    Club,
    District,
    Favorite,
    OperatingHour,
    ResourceBlock,
    SpecialSchedule,
    Zone,
)


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = ("name", "city", "status")
    show_change_link = True


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


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name","owner","status","is_verified","rating","review_count","created_at",)
    list_filter = ("status", "is_verified")
    search_fields = ("name", "owner__username", "owner__phone")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("rating", "review_count", "created_at", "updated_at")
    inlines = (BranchInline,)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "city", "district", "status")
    list_filter = ("status", "city", "district", "is_24_hours")
    search_fields = ("name","club__name","address","city__name","district__name",)
    autocomplete_fields = ("club", "city", "district")


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name","branch","resource_type","booking_type","status","capacity","unit_count","price_per_hour_tiyin","sort_order",)
    list_filter = ("resource_type", "booking_type", "status", "branch__club")
    search_fields = ("name", "branch__name", "branch__club__name")


@admin.register(ResourceBlock)
class ResourceBlockAdmin(admin.ModelAdmin):
    list_display = ("zone", "starts_at", "ends_at", "is_active")
    list_filter = ("is_active", "zone__branch__club")
    search_fields = ("reason", "zone__name")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "created_at")
    search_fields = ("user__username", "user__phone", "club__name")


admin.site.register(BranchImage)
admin.site.register(OperatingHour)
admin.site.register(SpecialSchedule)
