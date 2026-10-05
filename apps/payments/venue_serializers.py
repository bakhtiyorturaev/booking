from decimal import Decimal

from rest_framework import serializers

from apps.clubs.models import Club
from apps.payments.models import ManualVenuePayment
from apps.payments.venue_billing import venue_billing_status


class VenueBillingSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    monthly_price_tiyin = serializers.SerializerMethodField()
    paid_until = serializers.SerializerMethodField()
    billing_status = serializers.SerializerMethodField()
    remaining_days = serializers.SerializerMethodField()
    alert_level = serializers.SerializerMethodField()

    billing_enabled = serializers.SerializerMethodField()
    grace_until = serializers.SerializerMethodField()

    def get_billing_enabled(self, obj):
        return self.billing_snapshot(obj)["billing_enabled"]

    def get_grace_until(self, obj):
        return self.billing_snapshot(obj)["grace_until"]

    class Meta:
        model = Club
        fields = ("id", "name", "category", "owner", "owner_name", "monthly_price_tiyin", "paid_until", "billing_status", "remaining_days", "alert_level", "billing_enabled", "grace_until")
        read_only_fields = fields

    def billing_snapshot(self, obj):
        snapshots = self.context.setdefault("billing_snapshots", {})
        if obj.pk not in snapshots:
            snapshots[obj.pk] = venue_billing_status(obj)
        return snapshots[obj.pk]

    def get_owner_name(self, obj):
        profile = getattr(obj.owner, "profile", None)
        return (profile.full_name if profile else "") or obj.owner.username

    def get_monthly_price_tiyin(self, obj):
        return self.billing_snapshot(obj)["monthly_price_tiyin"]

    def get_paid_until(self, obj):
        billing = getattr(obj, "billing", None)
        return billing.paid_until if billing else None

    def get_billing_status(self, obj):
        return self.billing_snapshot(obj)["billing_status"]

    def get_remaining_days(self, obj):
        return self.billing_snapshot(obj)["remaining_days"]

    def get_alert_level(self, obj):
        return self.billing_snapshot(obj)["alert_level"]


MONEY_ERROR_KEYS = ("invalid", "required", "null", "max_digits", "max_decimal_places", "max_whole_digits", "min_value")


class TariffInputSerializer(serializers.Serializer):
    monthly_price = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"), error_messages={key: "payments.invalid_monthly_price" for key in MONEY_ERROR_KEYS})


class ManualPaymentInputSerializer(serializers.Serializer):
    club = serializers.UUIDField(required=False)
    barber = serializers.UUIDField(required=False)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"), error_messages={key: "payments.invalid_amount" for key in MONEY_ERROR_KEYS})
    method = serializers.ChoiceField(choices=ManualVenuePayment.Method.choices, error_messages={"invalid_choice": "payments.invalid_manual_method"})
    idempotency_key = serializers.UUIDField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if bool(attrs.get("club")) == bool(attrs.get("barber")):
            raise serializers.ValidationError("Muassasa yoki sartaroshdan bittasini tanlang.")
        return attrs


class ManualVenuePaymentSerializer(serializers.ModelSerializer):
    club = serializers.SerializerMethodField()
    club_name = serializers.SerializerMethodField()
    barber = serializers.SerializerMethodField()
    barber_name = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()
    received_by_name = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()

    class Meta:
        model = ManualVenuePayment
        fields = ("id", "club", "club_name", "barber", "barber_name", "client", "client_name", "received_by", "received_by_name", "amount_tiyin", "monthly_price_tiyin", "method", "period_starts_at", "period_ends_at", "duration_days", "note", "created_at")
        read_only_fields = fields

    def get_club(self, obj):
        return str(obj.billing.club_id) if obj.billing_id else None

    def get_club_name(self, obj):
        return obj.billing.club.name if obj.billing_id else ""

    def get_barber(self, obj):
        return str(obj.barber_billing.barber_id) if obj.barber_billing_id else None

    def get_barber_name(self, obj):
        return obj.barber_billing.barber.full_name if obj.barber_billing_id else ""

    def person_name(self, user):
        profile = getattr(user, "profile", None)
        return (profile.full_name if profile else "") or user.username

    def get_client_name(self, obj):
        return self.person_name(obj.client)

    def get_received_by_name(self, obj):
        return self.person_name(obj.received_by)

    def get_duration_days(self, obj):
        return str((Decimal(obj.amount_tiyin) * 30 / obj.monthly_price_tiyin).quantize(Decimal("0.000001")))


class BarberBillingSerializer(serializers.Serializer):
    def to_representation(self, instance):
        from apps.payments.barber_billing import barber_billing_status
        profile = getattr(instance.user, "profile", None)
        return {"id": str(instance.pk), "name": instance.full_name, "category": "BARBER", "owner": str(instance.user_id), "owner_name": (profile.full_name if profile else "") or instance.user.username, **barber_billing_status(instance)}


class FreeModeInputSerializer(serializers.Serializer):
    is_free = serializers.BooleanField()


class BranchBillingSerializer(serializers.Serializer):
    def to_representation(self, instance):
        club = instance.club
        status = venue_billing_status(club)
        if instance.is_free:
            status.update(billing_status="FREE", billing_enabled=False, alert_level="NONE")
        profile = getattr(club.owner, "profile", None)
        return {"id": str(instance.pk), "club_id": str(club.pk), "name": instance.name, "club_name": club.name, "category": club.category, "owner": str(club.owner_id), "owner_name": (profile.full_name if profile else "") or club.owner.username, "is_free": instance.is_free, **status}
