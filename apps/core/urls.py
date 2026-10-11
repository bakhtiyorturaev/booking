from django.urls import path

from apps.core.cabinet_views import AdminDashboardStatsAPIView
from apps.core.views import PublicServiceTypeListAPIView, TranslationListAPIView

urlpatterns = [
    path("", TranslationListAPIView.as_view(), name="translations"),
    path("service-types/", PublicServiceTypeListAPIView.as_view(), name="public-service-types"),
    path("cabinet/stats/", AdminDashboardStatsAPIView.as_view(), name="cabinet-stats"),
]
