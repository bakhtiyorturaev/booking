from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import normalize_language
from apps.core.services.translations import get_app_translations


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
