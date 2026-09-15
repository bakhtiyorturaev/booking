from rest_framework import serializers

from apps.payments.models import Payment, SubscriptionPlan


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
