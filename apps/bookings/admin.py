from django.contrib import admin

from apps.bookings.models import Booking, BookingHold, Cancellation


@admin.register(BookingHold)
class BookingHoldAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "zone", "starts_at", "expires_at", "status")
    list_filter = ("status",)
    search_fields = ("user__phone", "zone__name")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "zone", "starts_at", "status", "total_price_tiyin")
    list_filter = ("status",)
    search_fields = ("id", "user__phone", "zone__name")


admin.site.register(Cancellation)
