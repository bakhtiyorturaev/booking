from decimal import Decimal

from rest_framework import serializers

from apps.payments.models import ManualSubscriptionPayment, Payment, SubscriptionPlan


class SubscriptionStatusSerializer(serializers.Serializer):
    plan = serializers.ChoiceField(choices=("FREE", "PAID"))
    status = serializers.ChoiceField(
        choices=("FREE", "ACTIVE", "EXPIRED", "CANCELLED")
    )
    expires_at = serializers.DateTimeField(allow_null=True)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ("code", "name", "price_tiyin", "duration_days")
        read_only_fields = fields


class CheckoutCreateSerializer(serializers.Serializer):
    plan_code = serializers.SlugField(max_length=50)


class PaymentSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "plan",
            "amount_tiyin",
            "currency",
            "status",
            "checkout_url",
            "paid_at",
            "created_at",
        )
        read_only_fields = fields


class PaymentWebhookSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()
    external_id = serializers.CharField(max_length=150, required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=("PAID", "FAILED", "CANCELLED", "REFUNDED")
    )


MONEY_ERROR_KEYS = ("invalid", "required", "null", "max_digits", "max_decimal_places", "max_whole_digits", "min_value")


class ManualSubscriptionPaymentInputSerializer(serializers.Serializer):
    user = serializers.UUIDField()
    plan = serializers.SlugField(max_length=50)
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.01"), required=False,
        error_messages={key: "payments.invalid_amount" for key in MONEY_ERROR_KEYS},
    )
    method = serializers.ChoiceField(
        choices=ManualSubscriptionPayment.Method.choices,
        error_messages={"invalid_choice": "payments.invalid_manual_method"},
    )
    idempotency_key = serializers.UUIDField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class ManualSubscriptionPaymentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    plan_code = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()
    received_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ManualSubscriptionPayment
        fields = (
            "id", "user", "user_name", "plan_code", "plan_name",
            "received_by", "received_by_name", "amount_tiyin", "method",
            "note", "created_at",
        )
        read_only_fields = fields

    def get_user_name(self, obj):
        profile = getattr(obj.user, "profile", None)
        return (profile.full_name if profile else "") or obj.user.username

    def get_plan_code(self, obj):
        return obj.plan.code

    def get_plan_name(self, obj):
        return obj.plan.name

    def get_received_by_name(self, obj):
        profile = getattr(obj.received_by, "profile", None)
        return (profile.full_name if profile else "") or obj.received_by.username
