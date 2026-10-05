from django.db import IntegrityError
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.clubs.models import Club
from apps.clubs.permissions import is_platform_admin
from apps.payments.models import ManualVenuePayment
from apps.payments.venue_billing import PaymentConflict, record_venue_payment
from apps.payments.venue_serializers import (
    ManualPaymentInputSerializer, ManualVenuePaymentSerializer,
    VenueBillingSerializer,
)


class FreeModeMixin:
    @action(detail=True, methods=["post"], url_path="free-mode")
    def free_mode(self, request, pk=None):
        from apps.payments.venue_serializers import FreeModeInputSerializer
        self.require_staff()
        instance = self.get_object()
        serializer = FreeModeInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance.is_free = serializer.validated_data["is_free"]
        instance.save(update_fields=("is_free", "updated_at"))
        return Response(self.get_serializer(instance).data)


class BillingPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class BillingAccessMixin:
    permission_classes = [IsAuthenticated]
    pagination_class = BillingPagination
    allow_owner_reads = False

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not self.allow_owner_reads or self.action not in {"list", "retrieve"}:
            self.require_staff()

    def require_staff(self):
        if not is_platform_admin(self.request.user):
            self.permission_denied(self.request, message="clubs.permission_denied")


class CabinetVenueBillingViewSet(BillingAccessMixin, viewsets.ReadOnlyModelViewSet):
    allow_owner_reads = True
    serializer_class = VenueBillingSerializer
    queryset = Club.objects.none()

    def get_queryset(self):
        qs = Club.objects.select_related("owner__profile", "billing").exclude(status=Club.Status.ARCHIVED)
        if not is_platform_admin(self.request.user):
            qs = qs.filter(owner=self.request.user)
        query = self.request.query_params.get("query", "").strip()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(owner__username__icontains=query) | Q(owner__profile__full_name__icontains=query) | Q(owner__phone__icontains=query))
        club_id = self.request.query_params.get("club")
        if club_id:
            from rest_framework.serializers import UUIDField
            club_id = UUIDField().run_validation(club_id)
            qs = qs.filter(pk=club_id)
        return qs.order_by("name", "id")


    @action(detail=True, methods=["post"])
    def tariff(self, request, pk=None):
        self.permission_denied(request, message="Tarif faqat Django admin orqali belgilanadi.")


class CabinetManualVenuePaymentViewSet(BillingAccessMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ManualVenuePaymentSerializer
    queryset = ManualVenuePayment.objects.none()

    def get_queryset(self):
        qs = ManualVenuePayment.objects.select_related("billing__club", "barber_billing__barber", "client__profile", "received_by__profile")
        club_id = self.request.query_params.get("club")
        if club_id:
            from rest_framework.serializers import UUIDField
            club_id = UUIDField().run_validation(club_id)
            qs = qs.filter(billing__club_id=club_id)
        method = self.request.query_params.get("method")
        if method:
            qs = qs.filter(method=method)
        query = self.request.query_params.get("query", "").strip()
        if query:
            qs = qs.filter(Q(billing__club__name__icontains=query) | Q(barber_billing__barber__full_name__icontains=query) | Q(client__username__icontains=query) | Q(client__profile__full_name__icontains=query))
        return qs

    def create(self, request):
        self.require_staff()
        serializer = ManualPaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        club = get_object_or_404(Club.objects.exclude(status=Club.Status.ARCHIVED), pk=data["club"]) if data.get("club") else None
        from apps.barbers.models import Barber
        from apps.payments.barber_billing import record_barber_payment
        barber = get_object_or_404(Barber, pk=data["barber"]) if data.get("barber") else None
        try:
            recorder = record_venue_payment if club else record_barber_payment
            payment, created = recorder(
                **({"club": club} if club else {"barber": barber}), actor=request.user, amount_tiyin=int(data["amount"] * 100),
                method=data["method"], idempotency_key=data["idempotency_key"], note=data["note"],
            )
        except IntegrityError:
            if ManualVenuePayment.objects.filter(idempotency_key=data["idempotency_key"]).exists():
                raise PaymentConflict()
            raise
        return Response(self.get_serializer(payment).data, status=201 if created else 200)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.get_queryset()
        return Response({
            "total_tiyin": qs.aggregate(total=Sum("amount_tiyin"))["total"] or 0,
            "today_tiyin": qs.filter(created_at__date=timezone.localdate()).aggregate(total=Sum("amount_tiyin"))["total"] or 0,
            "cash_tiyin": qs.filter(method="CASH").aggregate(total=Sum("amount_tiyin"))["total"] or 0,
            "card_tiyin": qs.filter(method="CARD").aggregate(total=Sum("amount_tiyin"))["total"] or 0,
            "count": qs.count(),
        })


class CabinetBarberBillingViewSet(FreeModeMixin, BillingAccessMixin, viewsets.ReadOnlyModelViewSet):
    allow_owner_reads = True

    def get_serializer_class(self):
        from apps.payments.venue_serializers import BarberBillingSerializer
        return BarberBillingSerializer

    def get_queryset(self):
        from apps.barbers.models import Barber
        queryset = Barber.objects.select_related("user__profile", "branch", "billing").order_by("full_name", "id")
        if not is_platform_admin(self.request.user):
            queryset = queryset.filter(Q(user=self.request.user) | Q(club__owner=self.request.user))
        query = self.request.query_params.get("query", "").strip()
        if query:
            queryset = queryset.filter(Q(full_name__icontains=query) | Q(user__username__icontains=query))
        return queryset


class CabinetBranchBillingViewSet(FreeModeMixin, BillingAccessMixin, viewsets.ReadOnlyModelViewSet):
    allow_owner_reads = True

    def get_serializer_class(self):
        from apps.payments.venue_serializers import BranchBillingSerializer
        return BranchBillingSerializer

    def get_queryset(self):
        from apps.clubs.models import Branch
        qs = Branch.objects.select_related("club__owner__profile", "club__billing").exclude(status=Branch.Status.ARCHIVED).order_by("club__name", "name", "id")
        if not is_platform_admin(self.request.user):
            qs = qs.filter(club__owner=self.request.user)
        query = self.request.query_params.get("query", "").strip()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(club__name__icontains=query) | Q(club__owner__username__icontains=query))
        return qs
