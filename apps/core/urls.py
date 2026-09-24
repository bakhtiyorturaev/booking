from django.urls import path

from apps.core.cabinet_views import (
    AdminDashboardStatsAPIView,
    OwnerDashboardStatsAPIView,
)
from apps.core.views import TranslationListAPIView

urlpatterns = [
    path("", TranslationListAPIView.as_view(), name="translations"),
    path("cabinet/stats/", AdminDashboardStatsAPIView.as_view(), name="cabinet-stats"),
    path(
        "cabinet/owner-stats/",
        OwnerDashboardStatsAPIView.as_view(),
        name="cabinet-owner-stats",
    ),
]
