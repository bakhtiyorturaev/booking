from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.payments.cabinet_views import CabinetPaymentViewSet
from apps.payments.views import (
    CurrentSubscriptionAPIView,
    PaymentCheckoutAPIView,
    PaymentListAPIView,
    PaymentWebhookAPIView,
    SubscriptionPlanListAPIView,
)

router = DefaultRouter()
router.register("cabinet/payments", CabinetPaymentViewSet, basename="cabinet-payments")

urlpatterns = [
    path(
        "subscriptions/me/",
        CurrentSubscriptionAPIView.as_view(),
        name="current-subscription",
    ),
    path("subscriptions/plans/", SubscriptionPlanListAPIView.as_view(), name="plans"),
    path("payments/checkout/", PaymentCheckoutAPIView.as_view(), name="checkout"),
    path("payments/", PaymentListAPIView.as_view(), name="payment-list"),
    path("payments/webhook/", PaymentWebhookAPIView.as_view(), name="payment-webhook"),
    *router.urls,
]
