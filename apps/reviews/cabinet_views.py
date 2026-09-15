from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.clubs.permissions import is_platform_admin
from apps.core.responses import error_response, success_response
from apps.reviews.models import Review
from apps.reviews.serializers import PublicReviewSerializer
from apps.reviews.services import delete_review, refresh_barber_rating, refresh_club_rating


class CabinetReviewPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(tags=["Admin Cabinet"], summary="Barcha sharhlar ro‘yxati (Moderatsiya)"),
    retrieve=extend_schema(tags=["Admin Cabinet"], summary="Sharh tafsiloti"),
    destroy=extend_schema(tags=["Admin Cabinet"], summary="Sharhni o‘chirish"),
)
class CabinetReviewViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = PublicReviewSerializer
    pagination_class = CabinetReviewPagination
    queryset = Review.objects.all().select_related("user__profile", "club", "booking").order_by("-created_at")

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not is_platform_admin(request.user):
            self.permission_denied(request, message="clubs.permission_denied", code="clubs.permission_denied")

    def get_queryset(self):
        qs = super().get_queryset()
        club_id = self.request.query_params.get("club_id")
        is_visible = self.request.query_params.get("is_visible")
        rating = self.request.query_params.get("rating")
        query = self.request.query_params.get("query", "").strip()

        if club_id:
            qs = qs.filter(club_id=club_id)
        if is_visible in ["true", "True", "1"]:
            qs = qs.filter(is_visible=True)
        elif is_visible in ["false", "False", "0"]:
            qs = qs.filter(is_visible=False)
        if rating and rating.isdigit():
            qs = qs.filter(rating=int(rating))
        if query:
            qs = qs.filter(
                Q(comment__icontains=query)
                | Q(user__profile__full_name__icontains=query)
                | Q(user__username__icontains=query)
                | Q(club__name__icontains=query)
            )

        return qs

    def perform_destroy(self, instance):
        delete_review(instance)

    @extend_schema(
        tags=["Admin Cabinet"],
        summary="Sharh ko‘rinishini o‘zgartirish (Ko‘rsatish/Yashirish)",
        request=None,
    )
    @action(detail=True, methods=["post"], url_path="toggle-visibility")
    def toggle_visibility(self, request, pk=None):
        review = self.get_object()
        review.is_visible = not review.is_visible
        review.save(update_fields=["is_visible", "updated_at"])
        refresh_club_rating(review.club_id)
        if review.barber_id:
            refresh_barber_rating(review.barber_id)

        return success_response(
            "reviews.visibility_updated",
            request,
            data=PublicReviewSerializer(review).data,
        )
