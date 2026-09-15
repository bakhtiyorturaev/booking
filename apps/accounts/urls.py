from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts.cabinet_views import CabinetUserViewSet
from apps.accounts.views import (
    CurrentUserAPIView,
    LogoutAPIView,
    TelegramAuthConfigAPIView,
    TelegramContactAPIView,
    TelegramLoginAPIView,
    TelegramMiniAppLoginAPIView,
    TelegramWebLoginCheckAPIView,
    TelegramWebLoginInitAPIView,
    TokenRefreshAPIView,
)

app_name = "accounts"

router = DefaultRouter()
router.register("cabinet/users", CabinetUserViewSet, basename="cabinet-users")

urlpatterns = [
    path("auth/telegram/config/", TelegramAuthConfigAPIView.as_view(), name="telegram-config"),
    path("auth/telegram/", TelegramLoginAPIView.as_view(), name="telegram-login"),
    path("auth/telegram-miniapp/", TelegramMiniAppLoginAPIView.as_view(), name="telegram-miniapp-login"),
    path("auth/telegram-miniapp/contact/", TelegramContactAPIView.as_view(), name="telegram-contact"),
    path("auth/telegram-web/init/", TelegramWebLoginInitAPIView.as_view(), name="telegram-web-init"),
    path("auth/telegram-web/check/<str:token>/", TelegramWebLoginCheckAPIView.as_view(), name="telegram-web-check"),
    path("auth/me/", CurrentUserAPIView.as_view(), name="current-user"),
    path("auth/token/refresh/", TokenRefreshAPIView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutAPIView.as_view(), name="logout"),
    *router.urls,
]
