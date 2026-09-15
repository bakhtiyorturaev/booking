from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.reviews.cabinet_views import CabinetReviewViewSet
from apps.reviews.views import PublicClubReviewListAPIView, ReviewViewSet

router = DefaultRouter()
router.register("reviews", ReviewViewSet, basename="reviews")
router.register("cabinet/reviews", CabinetReviewViewSet, basename="cabinet-reviews")

urlpatterns = [
    path(
        "clubs/<uuid:club_id>/reviews/",
        PublicClubReviewListAPIView.as_view(),
        name="club-reviews",
    ),
    *router.urls,
]
