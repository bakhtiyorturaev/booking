from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.barbers.cabinet_views import CabinetBarberViewSet
from apps.barbers.views import (
    BarberAffiliateAPIView,
    BarberAvailabilityAPIView,
    BarberProfileAPIView,
    BarberStatusAPIView,
    PublicBarberViewSet,
)

router = DefaultRouter()
router.register("barbers", PublicBarberViewSet, basename="public-barber")
router.register("cabinet/barbers", CabinetBarberViewSet, basename="cabinet-barbers")

urlpatterns = [
    path("barbers/me/", BarberProfileAPIView.as_view(), name="barber-profile"),
    path("barbers/me/status/", BarberStatusAPIView.as_view(), name="barber-status"),
    path("barbers/me/affiliate/", BarberAffiliateAPIView.as_view(), name="barber-affiliate"),
    path("barbers/<uuid:pk>/availability/", BarberAvailabilityAPIView.as_view(), name="barber-availability"),
    path("", include(router.urls)),
]
