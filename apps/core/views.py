from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from apps.core.models import ServiceType, normalize_language
from apps.core.services.translations import get_app_translations
from apps.core.services.service_types import active_service_ids


class PublicServiceTypeSerializer(serializers.ModelSerializer):
    translations = serializers.SerializerMethodField()

    class Meta:
        model = ServiceType
        fields = ("id", "code", "name", "parent", "translations", "sort_order", "is_active")

    def get_translations(self, obj):
        return {"uz": obj.name, "ru": obj.name_ru or obj.name, "en": obj.name_en or obj.name}


class TranslationListAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Translations"],
        summary="Ilova tarjimalarini olish",
        parameters=[
            OpenApiParameter(
                name="lang",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Til kodi: uz, ru yoki en",
                required=False,
                enum=["uz", "ru", "en"],
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        language = normalize_language(
            request.query_params.get("lang")
        )

        return Response({
            "language": language,
            "translations": get_app_translations(language),
        })


class PublicServiceTypeListAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Services"],
        summary="Faol xizmat turlarini olish",
        responses={200: PublicServiceTypeSerializer(many=True)},
    )
    def get(self, request):
        services = ServiceType.objects.filter(pk__in=active_service_ids()).order_by("sort_order", "name")
        return Response(PublicServiceTypeSerializer(services, many=True).data)
