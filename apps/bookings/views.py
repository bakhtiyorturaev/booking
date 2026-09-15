from django.db.models import Q, Subquery
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking, BookingHold
from apps.bookings.serializers import (
    AvailabilityQuerySerializer,
    BarberBookingCreateSerializer,
    BookingListQuerySerializer,
    BranchAvailabilitySerializer,
    BookingHoldSerializer,
    BookingOperatorTransitionSerializer,
    BookingSerializer,
    CancellationSerializer,
)
from apps.bookings.services import get_branch_availability
from apps.clubs.models import Branch
from apps.clubs.permissions import IsClubOperator, is_platform_admin
from apps.payments.services import has_paid_access


class BookingPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100


#----------------------------------------------------------------
class BranchAvailabilityAPIView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=["Bookings"],
        summary="Bron uchun bo‘sh vaqtlarni olish",
        parameters=[
            OpenApiParameter("date", OpenApiTypes.DATE, required=True),
            OpenApiParameter("duration_minutes", OpenApiTypes.INT),
        ],
        responses=BranchAvailabilitySerializer,
    )
    def get(self, request, branch_id):
        branch = get_object_or_404(Branch, pk=branch_id, status=Branch.Status.ACTIVE)
        query = AvailabilityQuerySerializer(
            data=request.query_params,
            context={"branch": branch},
        )
        query.is_valid(raise_exception=True)
        target_date = query.validated_data["date"]
        availability = get_branch_availability(
            branch,
            target_date,
            query.validated_data.get("duration_minutes"),
        )
        return Response(
            {
                "branch_id": branch.id,
                "date": target_date,
                "zones": [
                    {
                        "id": item["zone"].id,
                        "name": item["zone"].name,
                        "capacity": item["zone"].capacity,
                        "booking_type": item["zone"].booking_type,
                        "unit_count": item["zone"].unit_count,
                        "price_per_hour_tiyin": item["zone"].price_per_hour_tiyin,
                        "slots": item["slots"],
                    }
                    for item in availability
                ],
            }
        )

@extend_schema_view(
    create=extend_schema(tags=["Bookings"], summary="Joyni vaqtincha band qilish"),
)
class BookingHoldViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = BookingHoldSerializer
    queryset = BookingHold.objects.all()

@extend_schema_view(
    list=extend_schema(
        tags=["Bookings"],
        summary="Mening bronlarimni olish",
        parameters=[
            OpenApiParameter("status", str, enum=Booking.Status.values),
            OpenApiParameter("scope", str, enum=["all", "upcoming", "past"]),
        ],
    ),
    create=extend_schema(tags=["Bookings"], summary="Hold asosida bron yaratish"),
    retrieve=extend_schema(tags=["Bookings"], summary="Bron tafsilotlarini olish"),
)
class BookingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated,)
    serializer_class = BookingSerializer
    pagination_class = BookingPagination
    queryset = Booking.objects.all()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        query = BookingListQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        queryset = self.queryset.filter(user=self.request.user).select_related(
            "zone__branch__city", "zone__branch__district", "zone__branch__club", "barber__club", "barber__branch", "cancellation"
        )
        if not has_paid_access(self.request.user):
            active = Q(
                status__in=(
                    Booking.Status.PENDING_CONFIRMATION,
                    Booking.Status.CONFIRMED,
                    Booking.Status.CHECKED_IN,
                ),
                ends_at__gt=timezone.now(),
            )
            history = queryset.exclude(active).order_by("-starts_at").values("pk")[:3]
            queryset = queryset.filter(active | Q(pk__in=Subquery(history)))
        booking_status = query.validated_data.get("status")
        if booking_status:
            queryset = queryset.filter(status=booking_status)
        scope = query.validated_data["scope"]
        if scope == "upcoming":
            queryset = queryset.filter(ends_at__gt=timezone.now())
        elif scope == "past":
            queryset = queryset.filter(ends_at__lte=timezone.now())
        return queryset

    @extend_schema(
        tags=["Bookings"],
        summary="Sartaroshni to'g'ridan-to'g'ri 1 soatga bron qilish",
        request=BarberBookingCreateSerializer,
        responses=BookingSerializer,
    )
    @action(detail=False, methods=("post",), url_path="barber")
    def barber(self, request):
        serializer = BarberBookingCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Bookings"],
        summary="Kutilayotgan yoki tasdiqlangan bronni bekor qilish",
        request=CancellationSerializer,
        responses=BookingSerializer,
    )
    @action(detail=True, methods=("post",))
    def cancel(self, request, pk=None):
        serializer = CancellationSerializer(
            data=request.data,
            context={"request": request, "booking_id": pk},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(tags=["Club Cabinet"], summary="Klub bronlarini olish"),
    retrieve=extend_schema(tags=["Club Cabinet"], summary="Klub broni tafsiloti"),
)
class CabinetBookingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = (IsAuthenticated, IsClubOperator)
    serializer_class = BookingSerializer
    pagination_class = BookingPagination
    queryset = Booking.objects.none()

    def get_queryset(self):
        queryset = Booking.objects.select_related(
            "user__profile", "zone__branch__club", "barber__club", "barber__branch", "cancellation"
        ).order_by("-created_at")
        if not is_platform_admin(self.request.user):
            queryset = queryset.filter(
                Q(zone__branch__club__owner=self.request.user)
                | Q(barber__club__owner=self.request.user)
            )
        booking_status = self.request.query_params.get("status")
        if booking_status in Booking.Status.values:
            queryset = queryset.filter(status=booking_status)
        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            queryset = queryset.filter(Q(zone__branch_id=branch_id) | Q(barber__branch_id=branch_id))
        club_id = self.request.query_params.get("club_id")
        if club_id:
            queryset = queryset.filter(Q(zone__branch__club_id=club_id) | Q(barber__club_id=club_id))
        barber_id = self.request.query_params.get("barber_id")
        if barber_id:
            queryset = queryset.filter(barber_id=barber_id)
        date = self.request.query_params.get("date")
        if date:
            queryset = queryset.filter(starts_at__date=date)
        query = self.request.query_params.get("query", "").strip()
        if query:
            queryset = queryset.filter(
                Q(user__username__icontains=query)
                | Q(user__phone__icontains=query)
                | Q(user__profile__full_name__icontains=query)
                | Q(zone__name__icontains=query)
                | Q(zone__branch__name__icontains=query)
                | Q(zone__branch__club__name__icontains=query)
                | Q(barber__full_name__icontains=query)
                | Q(barber__club__name__icontains=query)
            )
        return queryset.distinct()

    def _transition(self, request, pk, target_status):
        serializer = BookingOperatorTransitionSerializer(
            data=request.data,
            context={
                "request": request,
                "booking_id": pk,
                "target_status": target_status,
            },
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(BookingSerializer(booking).data)

    @extend_schema(tags=["Club Cabinet"], request=None, responses=BookingSerializer)
    @action(detail=True, methods=("post",), url_path="check-in")
    def check_in(self, request, pk=None):
        return self._transition(request, pk, Booking.Status.CHECKED_IN)

    @extend_schema(tags=["Club Cabinet"], request=None, responses=BookingSerializer)
    @action(detail=True, methods=("post",))
    def complete(self, request, pk=None):
        return self._transition(request, pk, Booking.Status.COMPLETED)

    @extend_schema(tags=["Club Cabinet"], request=None, responses=BookingSerializer)
    @action(detail=True, methods=("post",), url_path="no-show")
    def no_show(self, request, pk=None):
        return self._transition(request, pk, Booking.Status.NO_SHOW)

    @extend_schema(tags=["Club Cabinet"], request=CancellationSerializer, responses=BookingSerializer)
    @action(detail=True, methods=("post",))
    def cancel(self, request, pk=None):
        serializer = CancellationSerializer(
            data=request.data,
            context={"request": request, "booking_id": pk},
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(BookingSerializer(booking).data)
