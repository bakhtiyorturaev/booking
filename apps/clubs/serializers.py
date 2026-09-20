from django.db.models import Min
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

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
from apps.clubs.permissions import is_platform_admin


def image_url(image, request):
    if not image:
        return None
    url = image.url
    return request.build_absolute_uri(url) if request else url


class CleanModelSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance or self.Meta.model()
        for field, value in attrs.items():
            try:
                model_field = self.Meta.model._meta.get_field(field)
            except Exception:
                continue
            if not model_field.many_to_many and model_field.concrete:
                setattr(instance, field, value)
        try:
            instance.full_clean(exclude=self._model_validation_exclusions(attrs))
        except Exception as error:
            if hasattr(error, "message_dict"):
                raise serializers.ValidationError(error.message_dict) from error
            raise serializers.ValidationError(str(error)) from error
        return attrs

    def _model_validation_exclusions(self, attrs):
        writable = {
            field.source or field.field_name
            for field in self.fields.values()
            if not field.read_only and (field.source or field.field_name) != "*"
        }
        return [
            field.name
            for field in self.Meta.model._meta.fields
            if field.name not in writable and field.name not in attrs
        ]


class BranchImageSerializer(CleanModelSerializer):
    class Meta:
        model = BranchImage
        fields = ("id", "branch", "image", "sort_order", "is_cover")
        read_only_fields = ("id",)


class PublicBranchImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchImage
        fields = ("image", "is_cover")
        read_only_fields = fields


class OperatingHourSerializer(CleanModelSerializer):
    weekday_name = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = OperatingHour
        fields = ("id","branch","weekday","weekday_name","opens_at","closes_at","is_closed",)
        read_only_fields = ("id",)


class PublicOperatingHourSerializer(serializers.ModelSerializer):
    weekday_name = serializers.CharField(source="get_weekday_display", read_only=True)

    class Meta:
        model = OperatingHour
        fields = ("weekday", "weekday_name", "opens_at", "closes_at", "is_closed")
        read_only_fields = fields


class SpecialScheduleSerializer(CleanModelSerializer):
    class Meta:
        model = SpecialSchedule
        fields = ("id","branch","date","opens_at","closes_at","is_closed","note",)
        read_only_fields = ("id",)


class PublicSpecialScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialSchedule
        fields = ("date", "opens_at", "closes_at", "is_closed", "note")
        read_only_fields = fields


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name", "slug")
        read_only_fields = fields


class DistrictSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)

    class Meta:
        model = District
        fields = ("id", "city", "name", "slug")
        read_only_fields = fields


class ZoneSerializer(CleanModelSerializer):
    class Meta:
        model = Zone
        fields = (
            "id",
            "branch",
            "name",
            "description",
            "status",
            "capacity",
            "booking_type",
            "unit_count",
            "price_per_hour_tiyin",
            "sort_order",
            "resource_type",
        )
        read_only_fields = ("id",)


class PublicZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = (
            "id",
            "name",
            "description",
            "capacity",
            "booking_type",
            "unit_count",
            "price_per_hour_tiyin",
            "resource_type",
        )
        read_only_fields = fields


class BranchSummarySerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    district = DistrictSerializer(read_only=True)
    full_address = serializers.CharField(read_only=True)
    min_price_tiyin = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    service_types = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = ("id","name","address","full_address","city","district","latitude","longitude","is_24_hours","service_types",
                  "min_price_tiyin","cover_image","distance_km",)
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField(min_value=0, allow_null=True))
    def get_min_price_tiyin(self, obj):
        value = getattr(obj, "min_price_tiyin", None)
        if value is None:
            value = obj.zones.filter(
                status=Zone.Status.ACTIVE,
            ).aggregate(value=Min("price_per_hour_tiyin"))["value"]
        return value

    @extend_schema_field(OpenApiTypes.URI)
    def get_cover_image(self, obj):
        image = next((image for image in obj.images.all() if image.is_cover), None)
        return image_url(image.image, self.context.get("request")) if image else None

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_distance_km(self, obj):
        distances = self.context.get("branch_distances", {})
        value = distances.get(str(obj.id))
        return round(value, 2) if value is not None else None

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_service_types(self, obj):
        return sorted({zone.resource_type for zone in obj.zones.all()})


class PublicClubListSerializer(serializers.ModelSerializer):
    branches = BranchSummarySerializer(many=True, read_only=True)
    min_price_tiyin = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    service_types = serializers.SerializerMethodField()
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Club
        fields = (
            "id",
            "name",
            "category",
            "category_display",
            "slug",
            "description",
            "logo",
            "cover",
            "is_verified",
            "rating",
            "review_count",
            "service_types",
            "min_price_tiyin",
            "distance_km",
            "is_favorite",
            "branches",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.IntegerField(min_value=0, allow_null=True))
    def get_min_price_tiyin(self, obj):
        value = getattr(obj, "min_price_tiyin", None)
        if value is None:
            prices = [
                branch.min_price_tiyin
                for branch in obj.branches.all()
                if getattr(branch, "min_price_tiyin", None) is not None
            ]
            value = min(prices) if prices else None
        return value

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_distance_km(self, obj):
        distances = self.context.get("club_distances", {})
        value = distances.get(str(obj.id))
        return round(value, 2) if value is not None else None

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_favorite(self, obj):
        favorite_ids = self.context.get("favorite_club_ids", set())
        return obj.id in favorite_ids

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_service_types(self, obj):
        return sorted({
            zone.resource_type
            for branch in obj.branches.all()
            for zone in branch.zones.all()
        })


class PublicBranchDetailSerializer(serializers.ModelSerializer):
    club = serializers.SerializerMethodField()
    city = CitySerializer(read_only=True)
    district = DistrictSerializer(read_only=True)
    full_address = serializers.CharField(read_only=True)
    images = PublicBranchImageSerializer(many=True, read_only=True)
    operating_hours = PublicOperatingHourSerializer(many=True, read_only=True)
    special_schedules = PublicSpecialScheduleSerializer(many=True, read_only=True)
    zones = PublicZoneSerializer(many=True, read_only=True)
    min_price_tiyin = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = ("id","club","name","description","address","full_address","city","district","landmark","latitude","longitude",
                  "phone","timezone","slot_interval_minutes","minimum_booking_minutes","maximum_booking_minutes",
                  "booking_hold_minutes","advance_booking_days","free_cancellation_minutes","no_show_grace_minutes",
                  "auto_confirm_booking","is_24_hours","min_price_tiyin","distance_km","images",
                  "operating_hours","special_schedules","zones",)
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_club(self, obj):
        return {
            "id": str(obj.club_id),
            "name": obj.club.name,
            "category": obj.club.category,
            "category_display": obj.club.get_category_display(),
            "slug": obj.club.slug,
            "logo": image_url(obj.club.logo, self.context.get("request")),
            "rating": obj.club.rating,
            "review_count": obj.club.review_count,
        }

    @extend_schema_field(serializers.IntegerField(min_value=0, allow_null=True))
    def get_min_price_tiyin(self, obj):
        return getattr(obj, "min_price_tiyin", None)

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_distance_km(self, obj):
        distance = self.context.get("distance_km")
        return round(distance, 2) if distance is not None else None


class ClubManagementSerializer(CleanModelSerializer):
    class Meta:
        model = Club
        fields = (
            "id",
            "name",
            "category",
            "slug",
            "description",
            "logo",
            "cover",
            "phone",
            "email",
            "website",
            "status",
            "is_verified",
            "rating",
            "review_count",
        )
        read_only_fields = ("id", "slug", "rating", "review_count")

    def validate_status(self, value):
        request = self.context.get("request")
        if request and not is_platform_admin(request.user):
            allowed = {Club.Status.DRAFT, Club.Status.PENDING}
            current = self.instance.status if self.instance else Club.Status.DRAFT
            if value not in allowed and value != current:
                raise serializers.ValidationError("clubs.admin_only_status_change", code="clubs.admin_only_status_change")
        return value

    def validate_is_verified(self, value):
        request = self.context.get("request")
        if request and not is_platform_admin(request.user):
            current = self.instance.is_verified if self.instance else False
            if value != current:
                raise serializers.ValidationError("clubs.permission_denied", code="clubs.permission_denied")
        return value


class BranchManagementSerializer(CleanModelSerializer):
    class Meta:
        model = Branch
        fields = ("id","club","name","description","address","city","district","landmark","latitude","longitude",
                  "phone","timezone","status","slot_interval_minutes","minimum_booking_minutes",
                  "maximum_booking_minutes","booking_hold_minutes","advance_booking_days","free_cancellation_minutes",
                  "no_show_grace_minutes","auto_confirm_booking","is_24_hours",)
        read_only_fields = ("id",)

    def validate_city(self, value):
        if not value.is_active:
            raise serializers.ValidationError("clubs.active_city_only", code="clubs.active_city_only")
        return value

    def validate_district(self, value):
        if not value.is_active:
            raise serializers.ValidationError("clubs.active_district_only", code="clubs.active_district_only")
        return value


class ResourceBlockSerializer(CleanModelSerializer):
    class Meta:
        model = ResourceBlock
        fields = ("id","zone","starts_at","ends_at","reason","is_active",)
        read_only_fields = ("id",)


class FavoriteCreateSerializer(serializers.ModelSerializer):
    club = serializers.CharField(required=False, allow_null=True)
    branch = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Favorite
        fields = ("id", "club", "branch")
        read_only_fields = ("id",)

    def validate(self, attrs):
        raw_id = (
            attrs.get("club")
            or attrs.get("branch")
            or self.initial_data.get("club_id")
            or self.initial_data.get("branch_id")
            or self.initial_data.get("club")
            or self.initial_data.get("id")
        )
        if not raw_id:
            raise serializers.ValidationError({"club": "Club ID talab qilinadi."}, code="required")

        # 1. Check if raw_id is a Club
        from django.db.models import Q
        club = Club.objects.filter(status=Club.Status.ACTIVE).filter(
            Q(id=raw_id) | Q(slug=raw_id) if isinstance(raw_id, str) else Q(id=raw_id)
        ).first()

        # 2. Check if raw_id is a Branch
        if not club:
            branch = Branch.objects.filter(status=Branch.Status.ACTIVE).filter(
                Q(id=raw_id)
            ).select_related("club").first()
            if branch and branch.club.status == Club.Status.ACTIVE:
                club = branch.club

        # 3. Check if raw_id is a Barber
        if not club:
            try:
                from apps.barbers.models import Barber
                barber = Barber.objects.filter(id=raw_id).select_related("club").first()
                if barber and barber.club and barber.club.status == Club.Status.ACTIVE:
                    club = barber.club
            except Exception:
                pass

        if not club:
            raise serializers.ValidationError({"club": "clubs.active_club_only_favorites"}, code="clubs.active_club_only_favorites")

        attrs["resolved_club"] = club
        return attrs

    def create(self, validated_data):
        favorite, _ = Favorite.objects.get_or_create(
            user=self.context["request"].user,
            club=validated_data["resolved_club"],
        )
        return favorite


class FavoriteSerializer(serializers.ModelSerializer):
    club = PublicClubListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ("id", "club")
        read_only_fields = fields
