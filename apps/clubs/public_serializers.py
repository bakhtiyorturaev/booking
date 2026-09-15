from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.clubs.models import Club
from apps.clubs.serializers import BranchSummarySerializer
from apps.clubs.services.geo import haversine_km


class PublicClubBriefSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Club
        fields = ("id", "name", "category", "category_display", "slug", "logo", "rating", "review_count")
        read_only_fields = fields


class PublicBranchListSerializer(BranchSummarySerializer):
    club = PublicClubBriefSerializer(read_only=True)

    class Meta(BranchSummarySerializer.Meta):
        fields = ("club",) + BranchSummarySerializer.Meta.fields
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_distance_km(self, obj):
        latitude, longitude = self.context.get("location", (None, None))
        if latitude is None:
            return None
        return round(
            haversine_km(
                latitude,
                longitude,
                obj.latitude,
                obj.longitude,
            ),
            2,
        )
