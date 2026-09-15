from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(),
        name="api-schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="api-schema"),
        name="redoc",
    ),
    path("api/v1/",include("apps.core.urls"),),
    path("api/v1/",include("apps.accounts.urls"),),
    path("api/v1/",include("apps.clubs.urls"),),
    path("api/v1/", include("apps.barbers.urls")),
    path("api/v1/", include("apps.bookings.urls")),
    path("api/v1/", include("apps.reviews.urls")),
    path("api/v1/", include("apps.payments.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
