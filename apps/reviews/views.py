from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.reviews.models import Review
from apps.reviews.serializers import PublicReviewSerializer, ReviewSerializer
from apps.reviews.services import delete_review


class ReviewPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100


class PublicClubReviewListAPIView(generics.ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = PublicReviewSerializer
    pagination_class = ReviewPagination

    @extend_schema(tags=["Reviews"], summary="Klub sharhlarini olish")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Review.objects.filter(
            club_id=self.kwargs["club_id"],
            is_visible=True,
        ).select_related("user", "user__profile")


@extend_schema_view(
    list=extend_schema(tags=["Reviews"], summary="Mening sharhlarimni olish"),
    create=extend_schema(tags=["Reviews"], summary="Tugallangan bron uchun sharh yozish"),
    partial_update=extend_schema(tags=["Reviews"], summary="Sharhni yangilash"),
    destroy=extend_schema(tags=["Reviews"], summary="Sharhni o‘chirish"),
)
class ReviewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)
    serializer_class = ReviewSerializer
    pagination_class = ReviewPagination
    http_method_names = ("get", "post", "patch", "delete", "head", "options")
    queryset = Review.objects.all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        return self.queryset.filter(user=self.request.user).select_related(
            "booking",
            "club",
        )

    def perform_destroy(self, instance):
        delete_review(instance)
