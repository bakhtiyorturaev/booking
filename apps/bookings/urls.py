from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.bookings.views import (
    BookingHoldViewSet,
    BookingViewSet,
    BranchAvailabilityAPIView,
    CabinetBookingViewSet,
)

router = DefaultRouter()
router.register("booking-holds", BookingHoldViewSet, basename="booking-holds")
router.register("bookings", BookingViewSet, basename="bookings")
router.register("cabinet/bookings", CabinetBookingViewSet, basename="cabinet-bookings")

urlpatterns = [
    path(
        "branches/<uuid:branch_id>/availability/", BranchAvailabilityAPIView.as_view(),name="branch-availability",),


    *router.urls,
]
