from django.contrib import admin
from django import forms
from apps.core.services.service_types import descendant_service_ids

from apps.clubs.models import (
    Branch,
    BranchImage,
    Club,
    Favorite,
    OperatingHour,
    ResourceBlock,
    SpecialSchedule,
    Zone,
)


class ClubServicesForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = "__all__"

    def clean(self):
        data = super().clean()
        services = data.get("available_services")
        if self.instance.pk and services is not None:
            allowed = descendant_service_ids(service.pk for service in services)
            assigned = set(Branch.objects.filter(club=self.instance).values_list("enabled_services", flat=True)) - {None}
            if not assigned.issubset(allowed):
                self.add_error("available_services", "Avval bu xizmatni filiallardan olib tashlang.")
        return data


class BranchServicesForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = "__all__"

    def clean(self):
        data = super().clean()
        club, services = data.get("club"), data.get("enabled_services")
        if club and services is not None:
            enabled = {service.pk for service in services}
            allowed = descendant_service_ids(club.available_services.values_list("pk", flat=True))
            if not enabled.issubset(allowed):
                self.add_error("enabled_services", "Faqat ushbu klubga tegishli xizmatlarni tanlang.")
            if self.instance.pk:
                assigned = set(self.instance.zones.exclude(service_type=None).values_list("service_type_id", flat=True))
                if not assigned.issubset(descendant_service_ids(enabled)):
                    self.add_error("enabled_services", "Avval ushbu xizmatning zonalarini o‘zgartiring.")
        return data


class ZoneServicesForm(forms.ModelForm):
    class Meta:
        model = Zone
        fields = "__all__"

    def clean(self):
        data = super().clean()
        branch, service = data.get("branch"), data.get("service_type")
        if service:
            allowed = descendant_service_ids(branch.enabled_services.values_list("pk", flat=True)) if branch else set()
            if service.pk not in allowed or not service.is_active:
                self.add_error("service_type", "Xizmat ushbu filialga biriktirilmagan.")
            if service.code in Zone.ResourceType.values:
                data["resource_type"] = service.code
        return data


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = ("name", "city", "status")
    show_change_link = True


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    form = ClubServicesForm
    filter_horizontal = ("available_services",)
    list_display = ("name","owner","status","is_verified","rating","review_count","created_at",)
    list_filter = ("status", "is_verified")
    search_fields = ("name", "owner__username", "owner__phone")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("rating", "review_count", "created_at", "updated_at")
    inlines = (BranchInline,)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        club = form.instance
        if club.service_type_id and not club.available_services.exists():
            club.available_services.add(club.service_type_id)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    form = BranchServicesForm
    filter_horizontal = ("enabled_services",)
    list_display = ("name", "club", "city", "district", "status")
    list_filter = ("status", "city", "district", "is_24_hours")
    search_fields = ("name","club__name","address","city__name","district__name",)
    autocomplete_fields = ("club", "city", "district")


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    form = ZoneServicesForm
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
    list_display = ("user", "club", "barber", "created_at")
    search_fields = ("user__username", "user__phone", "club__name", "barber__full_name")


admin.site.register(BranchImage)
admin.site.register(OperatingHour)
admin.site.register(SpecialSchedule)
