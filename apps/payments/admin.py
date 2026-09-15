from django.contrib import admin

from apps.payments.models import Payment, SubscriptionPlan, UserSubscription


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "price_tiyin", "duration_days", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "plan", "amount_tiyin", "status", "created_at")
    list_filter = ("provider", "status", "created_at")
    search_fields = ("id", "external_id", "idempotency_key", "user__username")
    readonly_fields = (
        "id",
        "user",
        "plan",
        "provider",
        "external_id",
        "idempotency_key",
        "amount_tiyin",
        "currency",
        "status",
        "checkout_url",
        "paid_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "starts_at", "expires_at", "is_active")
    list_filter = ("status",)
    search_fields = ("user__username", "user__phone", "user__email")
    actions = ("activate_for_30_days",)

    @admin.action(description="Tanlangan obunalarni 30 kunga faollashtirish")
    def activate_for_30_days(self, request, queryset):
        for subscription in queryset:
            subscription.activate()
