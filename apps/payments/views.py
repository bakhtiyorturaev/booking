from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.payments.models import Payment, SubscriptionPlan
from apps.payments.serializers import (
    CheckoutCreateSerializer,
    PaymentSerializer,
    PaymentWebhookSerializer,
    SubscriptionPlanSerializer,
    SubscriptionStatusSerializer,
)
from apps.payments.services import (
    apply_payment_webhook,
    create_checkout,
    get_subscription_status,
    verify_webhook_signature,
)


class CurrentSubscriptionAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["Subscriptions"],
        summary="Joriy obuna holatini olish",
        responses=SubscriptionStatusSerializer,
    )
    def get(self, request):
        return Response(get_subscription_status(request.user))


@extend_schema_view(
    get=extend_schema(tags=["Subscriptions"], summary="Faol obuna tariflarini olish")
)
class SubscriptionPlanListAPIView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = SubscriptionPlanSerializer
    pagination_class = None
    queryset = SubscriptionPlan.objects.filter(is_active=True)


class PaymentCheckoutAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["Payments"],
        summary="Obuna uchun to‘lov yaratish",
        request=CheckoutCreateSerializer,
        responses={201: PaymentSerializer},
    )
    def post(self, request):
        serializer = CheckoutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = create_checkout(
            request.user,
            serializer.validated_data["plan_code"],
            request.headers.get("Idempotency-Key"),
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentListAPIView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PaymentSerializer

    @extend_schema(tags=["Payments"], summary="Mening to‘lovlarimni olish")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).select_related("plan")


class PaymentWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Payments"],
        summary="To‘lov provider webhooki",
        request=PaymentWebhookSerializer,
        responses={200: PaymentSerializer},
    )
    def post(self, request):
        if not verify_webhook_signature(
            request.body,
            request.headers.get("X-Payment-Signature", ""),
        ):
            return Response({"code": "payments.invalid_webhook_signature"}, status=status.HTTP_403_FORBIDDEN)
        serializer = PaymentWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = apply_payment_webhook(**serializer.validated_data)
        return Response(PaymentSerializer(payment).data)
