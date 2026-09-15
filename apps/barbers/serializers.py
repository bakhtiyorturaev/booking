from rest_framework import serializers

from apps.barbers.models import Barber
from apps.clubs.models import Branch, Club
from apps.clubs.services.geo import haversine_km


class PublicBarberSerializer(serializers.ModelSerializer):
    club_name = serializers.CharField(source="club.name", read_only=True, default="")
    club_slug = serializers.CharField(source="club.slug", read_only=True, default="")
    branch_name = serializers.CharField(source="branch.name", read_only=True, default="")
    branch_address = serializers.CharField(source="branch.full_address", read_only=True, default="")
    branch_city = serializers.CharField(source="branch.city.name", read_only=True, default="")
    branch_district = serializers.CharField(source="branch.district.name", read_only=True, default="")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    affiliation_status_display = serializers.CharField(
        source="get_affiliation_status_display",
        read_only=True,
    )
    distance_km = serializers.SerializerMethodField()

    def get_distance_km(self, obj):
        if not obj.branch or obj.branch.latitude is None or obj.branch.longitude is None:
            return None
        latitude = self.context.get("latitude")
        longitude = self.context.get("longitude")
        if latitude is None or longitude is None:
            return None
        try:
            return haversine_km(float(latitude), float(longitude), float(obj.branch.latitude), float(obj.branch.longitude))
        except (TypeError, ValueError):
            return None

    class Meta:
        model = Barber
        fields = (
            "id",
            "full_name",
            "phone",
            "photo",
            "status",
            "status_display",
            "rating",
            "review_count",
            "distance_km",
            "club",
            "club_name",
            "club_slug",
            "branch",
            "branch_name",
            "branch_address",
            "branch_city",
            "branch_district",
            "affiliation_status",
            "affiliation_status_display",
            "work_start_time",
            "work_end_time",
            "working_days",
            "is_active",
        )


class BarberProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barber
        fields = (
            "id",
            "full_name",
            "phone",
            "photo",
            "status",
            "work_start_time",
            "work_end_time",
            "working_days",
            "club",
            "branch",
            "affiliation_status",
            "rating",
            "review_count",
        )
        read_only_fields = ("id", "rating", "review_count", "affiliation_status")


class BarberStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Barber.Status.choices)


class BarberAffiliateSerializer(serializers.Serializer):
    club_id = serializers.UUIDField()
    branch_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        club_id = attrs.get("club_id")
        branch_id = attrs.get("branch_id")
        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            raise serializers.ValidationError({"club_id": "Sartaroshxona topilmadi."})

        branch = None
        if branch_id:
            try:
                branch = Branch.objects.get(id=branch_id, club=club)
            except Branch.DoesNotExist:
                raise serializers.ValidationError({"branch_id": "Filial topilmadi."})

        attrs["club"] = club
        attrs["branch"] = branch
        return attrs


class CabinetBarberSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True, default="")
    branch_name = serializers.CharField(source="branch.name", read_only=True, default="")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    affiliation_status_display = serializers.CharField(
        source="get_affiliation_status_display",
        read_only=True,
    )

    class Meta:
        model = Barber
        fields = (
            "id",
            "user",
            "user_username",
            "full_name",
            "phone",
            "photo",
            "club",
            "club_name",
            "branch",
            "branch_name",
            "status",
            "status_display",
            "affiliation_status",
            "affiliation_status_display",
            "work_start_time",
            "work_end_time",
            "working_days",
            "rating",
            "review_count",
            "is_active",
            "created_at",
            "updated_at",
        )
