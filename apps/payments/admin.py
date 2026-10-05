from decimal import Decimal
from django import forms
from django.contrib import admin

from apps.payments.models import ManualVenuePayment, Payment, SubscriptionPlan, UserSubscription, VenueBilling, VenueTariffRule, BarberBilling


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


@admin.register(ManualVenuePayment)
class ManualVenuePaymentAdmin(PaymentAdmin):
    list_display = ("id", "billing", "client", "received_by", "amount_tiyin", "method", "created_at")
    list_filter = ("method", "created_at")
    search_fields = ("billing__club__name", "client__username", "received_by__username")
    readonly_fields = tuple(field.name for field in ManualVenuePayment._meta.fields)


@admin.register(VenueBilling)
class VenueBillingAdmin(PaymentAdmin):
    list_display = ("club", "monthly_price_tiyin", "paid_until", "updated_at")
    list_filter = ()
    search_fields = ("club__name", "club__owner__username")
    readonly_fields = tuple(field.name for field in VenueBilling._meta.fields)


class VenueTariffRuleForm(forms.ModelForm):
    monthly_price = forms.DecimalField(label="30 kunlik narx, so‘m", min_value=Decimal("0.01"), max_digits=14, decimal_places=2)

    class Meta:
        model = VenueTariffRule
        exclude = ("monthly_price_tiyin",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["monthly_price"].initial = Decimal(self.instance.monthly_price_tiyin) / 100

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.monthly_price_tiyin = int(self.cleaned_data["monthly_price"] * 100)
        if commit:
            instance.save()
        return instance


@admin.register(VenueTariffRule)
class VenueTariffRuleAdmin(admin.ModelAdmin):
    form = VenueTariffRuleForm
    list_display = ("service_type", "city", "district", "monthly_price_som")
    list_filter = ("service_type", "city")
    autocomplete_fields = ("service_type", "city", "district")
    fields = ("service_type", "city", "district", "monthly_price")

    @admin.display(description="30 kunlik narx, so‘m")
    def monthly_price_som(self, obj):
        return f"{Decimal(obj.monthly_price_tiyin) / 100:,.2f}".replace(",", " ")

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(BarberBilling)
class BarberBillingAdmin(PaymentAdmin):
    list_display = ("barber", "monthly_price_tiyin", "paid_until")
    list_filter = ()
    search_fields = ("barber__full_name",)
    readonly_fields = tuple(field.name for field in BarberBilling._meta.fields)
