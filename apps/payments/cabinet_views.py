from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.clubs.permissions import is_platform_admin
from apps.payments.models import ManualSubscriptionPayment, Payment, SubscriptionPlan, UserSubscription
from apps.payments.serializers import (
    ManualSubscriptionPaymentInputSerializer,
    ManualSubscriptionPaymentSerializer,
    PaymentSerializer,
    SubscriptionPlanSerializer,
)
from apps.payments.subscription_billing import record_subscription_payment
from apps.payments.venue_billing import PaymentConflict


class CabinetPaymentPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(tags=["Admin Cabinet"], summary="Barcha to‘lovlar ro‘yxati"),
    retrieve=extend_schema(tags=["Admin Cabinet"], summary="To‘lov tafsiloti"),
)
class CabinetPaymentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    pagination_class = CabinetPaymentPagination
    queryset = Payment.objects.all().select_related("user__profile", "plan").order_by("-created_at")

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not is_platform_admin(request.user):
            self.permission_denied(request, message="clubs.permission_denied", code="clubs.permission_denied")

    def get_queryset(self):
        qs = super().get_queryset()
        payment_status = self.request.query_params.get("status")
        provider = self.request.query_params.get("provider")
        query = self.request.query_params.get("query", "").strip()

        if payment_status and payment_status in Payment.Status.values:
            qs = qs.filter(status=payment_status)
        if provider:
            qs = qs.filter(provider=provider)
        if query:
            qs = qs.filter(
                Q(user__username__icontains=query)
                | Q(user__phone__icontains=query)
                | Q(user__profile__full_name__icontains=query)
                | Q(external_id__icontains=query)
            )

        return qs

    @extend_schema(
        tags=["Admin Cabinet"],
        summary="Mijoz obunasini qo'lda faollashtirish (naqd/karta to'lovi)",
        request=ManualSubscriptionPaymentInputSerializer,
        responses={201: ManualSubscriptionPaymentSerializer, 200: ManualSubscriptionPaymentSerializer},
    )
    @action(detail=False, methods=["post"], url_path="activate-subscription")
    def activate_subscription(self, request):
        # Haqiqiy onlayn to'lov provayderi (PAYMENT_PROVIDER=http) hali
        # ulanmagan bo'lsa, mijoz o'z-o'zicha obuna sotib ololmaydi
        # (`create_checkout` doim `provider_not_configured` qaytaradi).
        # Shu yerda xodim naqd/karta to'lovini qayd etib, obunani qo'lda
        # faollashtiradi (H-10).
        serializer = ManualSubscriptionPaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        target_user = get_object_or_404(get_user_model(), pk=data["user"])
        try:
            payment, created = record_subscription_payment(
                user=target_user,
                actor=request.user,
                plan_code=data["plan"],
                method=data["method"],
                idempotency_key=data["idempotency_key"],
                amount_tiyin=int(data["amount"] * 100) if data.get("amount") is not None else None,
                note=data["note"],
            )
        except IntegrityError:
            if ManualSubscriptionPayment.objects.filter(idempotency_key=data["idempotency_key"]).exists():
                raise PaymentConflict()
            raise
        return Response(
            ManualSubscriptionPaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Admin Cabinet"],
        summary="To‘lovlar statistikasi xulosasi",
    )
    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        total_paid_sum = (
            Payment.objects.filter(status=Payment.Status.PAID).aggregate(
                total=Sum("amount_tiyin")
            )["total"]
            or 0
        )
        total_paid_count = Payment.objects.filter(status=Payment.Status.PAID).count()
        total_pending_count = Payment.objects.filter(status=Payment.Status.PENDING).count()
        total_failed_count = Payment.objects.filter(status=Payment.Status.FAILED).count()

        return Response(
            {
                "total_paid_sum_tiyin": total_paid_sum,
                "total_paid_count": total_paid_count,
                "total_pending_count": total_pending_count,
                "total_failed_count": total_failed_count,
            }
        )
