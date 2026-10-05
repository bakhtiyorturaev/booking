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
    can_manage_affiliation = serializers.SerializerMethodField()

    def get_can_manage_affiliation(self, obj):
        from apps.clubs.permissions import is_platform_admin
        user = self.context["request"].user
        return is_platform_admin(user) or bool(obj.club_id and obj.club.owner_id == user.pk)

    user_username = serializers.CharField(source="user.username", read_only=True)
    club_name = serializers.CharField(source="club.name", read_only=True, default="")
    branch_name = serializers.CharField(source="branch.name", read_only=True, default="")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    affiliation_status_display = serializers.CharField(
        source="get_affiliation_status_display",
        read_only=True,
    )

    billing = serializers.SerializerMethodField()

    def get_billing(self, obj):
        from apps.payments.barber_billing import barber_billing_status
        return barber_billing_status(obj)

    def validate(self, attrs):
        user = attrs.get("user", self.instance.user if self.instance else None)
        if user and (not user.is_active or user.role not in {"CUSTOMER", "CLIENT"}):
            raise serializers.ValidationError({"user": "Faol mijoz yoki sartarosh akkauntini tanlang."})
        days = attrs.get("working_days", self.instance.working_days if self.instance else [])
        if not isinstance(days, list) or any(type(day) is not int or day < 1 or day > 7 for day in days):
            raise serializers.ValidationError({"working_days": "Hafta kunlari 1 dan 7 gacha bo‘lishi kerak."})
        city = attrs.get("billing_city", self.instance.billing_city if self.instance else None)
        district = attrs.get("billing_district", self.instance.billing_district if self.instance else None)
        if district and district.city_id != (city.pk if city else None):
            raise serializers.ValidationError({"billing_district": "Tuman tanlangan shaharga tegishli emas."})
        club = attrs.get("club", self.instance.club if self.instance else None)
        branch = attrs.get("branch", self.instance.branch if self.instance else None)
        if branch and (not club or branch.club_id != club.pk):
            raise serializers.ValidationError({"branch": "Filial tanlangan muassasaga tegishli emas."})
        if club and club.category != "BARBERSHOP":
            raise serializers.ValidationError({"club": "Sartaroshxona tanlang."})
        return attrs

    class Meta:
        model = Barber
        read_only_fields = ("is_free", "rating", "review_count", "created_at", "updated_at")
        fields = (
            "id",
            "can_manage_affiliation",
            "is_free",
            "billing_city",
            "billing_district",
            "billing",
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
