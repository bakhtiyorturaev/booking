from django.db.models import Q, Sum
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.clubs.permissions import is_platform_admin
from apps.payments.models import Payment, SubscriptionPlan, UserSubscription
from apps.payments.serializers import PaymentSerializer, SubscriptionPlanSerializer


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
