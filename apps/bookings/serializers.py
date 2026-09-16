from datetime import timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import exceptions, serializers

from apps.bookings.models import Booking, BookingHold
from apps.bookings.services import (
    cancel_booking,
    create_booking,
    create_hold,
    transition_booking_for_operator,
)
from apps.clubs.models import Zone


def _raise_service_error(error):
    if isinstance(error, ObjectDoesNotExist):
        raise exceptions.NotFound("bookings.not_found", code="bookings.not_found") from error
    raise serializers.ValidationError(error.messages, code=error.code) from error


class AvailabilityQuerySerializer(serializers.Serializer):
    date = serializers.DateField(
        error_messages={"required": "bookings.invalid_date_format", "invalid": "bookings.invalid_date_format"},
    )
    duration_minutes = serializers.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            "invalid": "bookings.duration_must_be_integer",
            "min_value": "bookings.duration_invalid_for_branch",
        },
    )

    def validate_date(self, value):
        branch = self.context["branch"]
        today = timezone.localtime(
            timezone.now(),
            ZoneInfo(branch.timezone),
        ).date()
        if value < today:
            raise serializers.ValidationError("bookings.invalid_time_range", code="bookings.invalid_time_range")
        if value > today + timedelta(days=branch.advance_booking_days):
            raise serializers.ValidationError("bookings.date_outside_advance_limit", code="bookings.date_outside_advance_limit")
        return value

    def validate_duration_minutes(self, value):
        branch = self.context["branch"]
        if (
            not branch.minimum_booking_minutes <= value <= branch.maximum_booking_minutes
            or value % branch.slot_interval_minutes
        ):
            raise serializers.ValidationError("bookings.duration_invalid_for_branch", code="bookings.duration_invalid_for_branch")
        return value


class BookingListQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Booking.Status.choices,
        required=False,
        error_messages={"invalid_choice": "bookings.invalid_filter"},
    )
    scope = serializers.ChoiceField(
        choices=("all", "upcoming", "past"),
        default="all",
        error_messages={"invalid_choice": "bookings.invalid_filter"},
    )


class BookingHoldSerializer(serializers.ModelSerializer):
    zone_id = serializers.UUIDField(
        error_messages={"required": "bookings.id_invalid", "invalid": "bookings.id_invalid"},
    )

    class Meta:
        model = BookingHold
        fields = (
            "id",
            "zone_id",
            "starts_at",
            "ends_at",
            "quantity",
            "unit_price_tiyin",
            "total_price_tiyin",
            "status",
            "expires_at",
        )
        read_only_fields = (
            "unit_price_tiyin",
            "total_price_tiyin",
            "status",
            "expires_at",
        )
        extra_kwargs = {
            "starts_at": {
                "error_messages": {"required": "bookings.invalid_time_range", "invalid": "bookings.invalid_time_range"},
            },
            "ends_at": {
                "error_messages": {"required": "bookings.invalid_time_range", "invalid": "bookings.invalid_time_range"},
            },
            "quantity": {
                "error_messages": {"invalid": "bookings.invalid_quantity", "min_value": "bookings.invalid_quantity"},
            },
        }

    def create(self, validated_data):
        try:
            return create_hold(
                user=self.context["request"].user,
                zone_id=validated_data.pop("zone_id"),
                **validated_data,
            )
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _raise_service_error(error)


class BarberBookingCreateSerializer(serializers.Serializer):
    barber_id = serializers.UUIDField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        from apps.barbers.models import Barber
        try:
            barber = Barber.objects.get(id=attrs["barber_id"], is_active=True)
        except Barber.DoesNotExist:
            raise serializers.ValidationError({"barber_id": "Sartarosh topilmadi."})

        starts_at = attrs["starts_at"]
        ends_at = attrs.get("ends_at") or (starts_at + timedelta(hours=1))

        if ends_at <= starts_at:
            raise serializers.ValidationError({"ends_at": "Tugash vaqti boshlanishdan keyin bo'lishi kerak."})

        # Check for overlaps with active bookings for this barber
        overlap = Booking.objects.filter(
            barber=barber,
            status__in=[
                Booking.Status.CONFIRMED,
                Booking.Status.CHECKED_IN,
                Booking.Status.PENDING_CONFIRMATION,
            ],
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        ).exists()

        if overlap:
            raise serializers.ValidationError("Tanlangan vaqt allaqachon band qilingan.")

        attrs["barber"] = barber
        attrs["ends_at"] = ends_at
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        barber = validated_data["barber"]
        starts_at = validated_data["starts_at"]
        ends_at = validated_data["ends_at"]

        booking = Booking.objects.create(
            user=user,
            barber=barber,
            starts_at=starts_at,
            ends_at=ends_at,
            quantity=1,
            unit_price_tiyin=0,
            total_price_tiyin=0,
            status=Booking.Status.CONFIRMED,
            confirmed_at=timezone.now(),
        )

        from apps.barbers.services import send_barber_booking_notification
        send_barber_booking_notification(booking)

        from telegram_bot.services import send_customer_booking_notification
        send_customer_booking_notification(booking, Booking.Status.CONFIRMED)

        return booking


class BookingSerializer(serializers.ModelSerializer):
    zone = serializers.SerializerMethodField()
    barber = serializers.SerializerMethodField()
    cancellation_reason = serializers.CharField(
        source="cancellation.reason",
        read_only=True,
        default="",
    )
    hold_id = serializers.UUIDField(
        write_only=True,
        required=False,
        error_messages={"required": "bookings.id_invalid", "invalid": "bookings.id_invalid"},
    )

    class Meta:
        model = Booking
        fields = (
            "id",
            "booking_number",
            "hold_id",
            "zone_id",
            "zone",
            "barber_id",
            "barber",
            "starts_at",
            "ends_at",
            "quantity",
            "unit_price_tiyin",
            "total_price_tiyin",
            "status",
            "confirmed_at",
            "checked_in_at",
            "completed_at",
            "no_show_at",
            "cancellation_reason",
            "created_at",
        )
        read_only_fields = (
            "booking_number",
            "zone_id",
            "zone",
            "barber_id",
            "barber",
            "starts_at",
            "ends_at",
            "quantity",
            "unit_price_tiyin",
            "total_price_tiyin",
            "status",
            "confirmed_at",
            "checked_in_at",
            "completed_at",
            "no_show_at",
            "cancellation_reason",
            "created_at",
        )

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_zone(self, obj):
        if not obj.zone:
            return None
        branch = obj.zone.branch
        return {
            "id": str(obj.zone_id),
            "name": obj.zone.name,
            "resource_type": obj.zone.resource_type,
            "booking_type": obj.zone.booking_type,
            "branch": {
                "id": str(branch.id),
                "name": branch.name,
                "full_address": branch.full_address,
                "timezone": branch.timezone,
                "club": {
                    "id": str(branch.club_id),
                    "name": branch.club.name,
                    "slug": branch.club.slug,
                },
            },
        }

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_barber(self, obj):
        if not obj.barber:
            return None
        barber = obj.barber
        return {
            "id": str(barber.id),
            "full_name": barber.full_name,
            "phone": barber.phone,
            "photo": barber.photo.url if barber.photo else None,
            "status": barber.status,
            "status_display": barber.get_status_display(),
            "rating": str(barber.rating),
            "club": {
                "id": str(barber.club_id) if barber.club_id else None,
                "name": barber.club.name if barber.club else "",
                "slug": barber.club.slug if barber.club else "",
            } if barber.club else None,
            "branch": {
                "id": str(barber.branch_id) if barber.branch_id else None,
                "name": barber.branch.name if barber.branch else "",
            } if barber.branch else None,
        }

    def create(self, validated_data):
        try:
            return create_booking(
                user=self.context["request"].user,
                hold_id=validated_data["hold_id"],
            )
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _raise_service_error(error)


class CancellationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, allow_blank=True, required=False)

    def save(self, **kwargs):
        try:
            return cancel_booking(
                user=self.context["request"].user,
                booking_id=self.context["booking_id"],
                reason=self.validated_data.get("reason", ""),
            )
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _raise_service_error(error)


class BookingOperatorTransitionSerializer(serializers.Serializer):
    def save(self, **kwargs):
        try:
            return transition_booking_for_operator(
                self.context["request"].user,
                self.context["booking_id"],
                self.context["target_status"],
            )
        except PermissionError as error:
            raise exceptions.PermissionDenied("clubs.permission_denied", code="clubs.permission_denied") from error
        except (DjangoValidationError, ObjectDoesNotExist) as error:
            _raise_service_error(error)


class AvailabilitySlotSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    available = serializers.IntegerField(min_value=0)


class ZoneAvailabilitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    capacity = serializers.IntegerField(min_value=1)
    booking_type = serializers.ChoiceField(choices=Zone.BookingType.choices)
    unit_count = serializers.IntegerField(min_value=1)
    price_per_hour_tiyin = serializers.IntegerField(min_value=0)
    slots = AvailabilitySlotSerializer(many=True)


class BranchAvailabilitySerializer(serializers.Serializer):
    branch_id = serializers.UUIDField()
    date = serializers.DateField()
    zones = ZoneAvailabilitySerializer(many=True)
