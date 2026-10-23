import datetime

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clubs.permissions import IsBarberSelfOrPlatformAdmin
from apps.clubs.views import StandardPagination
from apps.barbers.models import Barber
from apps.barbers.serializers import (
    BarberAffiliateSerializer,
    BarberProfileSerializer,
    BarberStatusSerializer,
    PublicBarberListSerializer,
    PublicBarberSerializer,
)
from apps.barbers.services import get_barber_available_slots
from apps.clubs.services.geo import haversine_km
from django.db.models import Q

class PublicBarberViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Ommaviy sartaroshlar katalogi.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PublicBarberSerializer
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == "list":
            return PublicBarberListSerializer
        return super().get_serializer_class()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["latitude"] = self.request.query_params.get("latitude")
        context["longitude"] = self.request.query_params.get("longitude")
        return context

    def get_queryset(self):
        queryset = Barber.objects.filter(is_active=True).select_related(
            "club", "branch", "branch__city", "branch__district"
        )
        club_id = self.request.query_params.get("club_id")
        branch_id = self.request.query_params.get("branch_id")
        status_val = self.request.query_params.get("status")
        query = self.request.query_params.get("search") or self.request.query_params.get("query")
        city = self.request.query_params.get("city")
        ordering = self.request.query_params.get("ordering", "-rating")

        if club_id:
            queryset = queryset.filter(club_id=club_id)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if status_val:
            queryset = queryset.filter(status=status_val)
        if query:
            queryset = queryset.filter(
                Q(full_name__icontains=query) |
                Q(club__name__icontains=query) |
                Q(branch__name__icontains=query)
            )
        if city:
            queryset = queryset.filter(
                Q(branch__city__name__icontains=city) |
                Q(club__branches__city__name__icontains=city)
            ).distinct()

        if ordering in ["-rating", "rating", "full_name", "-full_name", "-review_count"]:
            queryset = queryset.order_by(ordering)
        elif ordering != "distance":
            queryset = queryset.order_by("-rating")

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        ordering = request.query_params.get("ordering")
        lat = request.query_params.get("latitude")
        lng = request.query_params.get("longitude")

        if ordering == "distance" and lat is not None and lng is not None:
            try:
                lat_f = float(lat)
                lng_f = float(lng)
                items = list(queryset)

                def get_dist(b):
                    point = b.map_coordinates
                    if point is not None:
                        try:
                            return haversine_km(lat_f, lng_f, float(point[0]), float(point[1]))
                        except (ValueError, TypeError):
                            return float("inf")
                    return float("inf")

                items.sort(key=get_dist)
                page = self.paginate_queryset(items)
                serializer = self.get_serializer(page if page is not None else items, many=True)
                if page is not None:
                    return self.get_paginated_response(serializer.data)
                return Response(serializer.data)
            except (ValueError, TypeError):
                pass

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class BarberAvailabilityAPIView(APIView):
    """
    Sartaroshning tanlangan kungi 1 soatlik bo'sh vaqt slotlari.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        barber = get_object_or_404(Barber, pk=pk, is_active=True)
        date_str = request.query_params.get("date")

        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                return Response(
                    {"detail": "Sana formati noto'g'ri (YYYY-MM-DD bo'lishi kerak)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = timezone.localdate()

        data = get_barber_available_slots(barber, target_date)
        return Response(data)


class BarberProfileAPIView(APIView):
    """
    Sartaroshning o'z shaxsiy profilini olish va tahrirlash.
    """
    permission_classes = [permissions.IsAuthenticated, IsBarberSelfOrPlatformAdmin]

    def get(self, request):
        barber = get_object_or_404(Barber, user=request.user)
        serializer = BarberProfileSerializer(barber)
        return Response(serializer.data)

    def patch(self, request):
        # Sartarosh yozuvini faqat platforma admini yaratadi
        # (`CabinetBarberViewSet.perform_create`); foydalanuvchi o'zini
        # sartarosh deb e'lon qila olmasligi kerak.
        barber = get_object_or_404(Barber, user=request.user)
        serializer = BarberProfileSerializer(barber, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BarberStatusAPIView(APIView):
    """
    Sartarosh o'zining real vaqt holatini (Ishda, Tanaffusda, Ishga chiqmagan, Dam olish kuni) tezkor o'zgartirishi.
    """
    permission_classes = [permissions.IsAuthenticated, IsBarberSelfOrPlatformAdmin]

    def post(self, request):
        return self._update_status(request)

    def patch(self, request):
        return self._update_status(request)

    def _update_status(self, request):
        barber = get_object_or_404(Barber, user=request.user)
        serializer = BarberStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        barber.status = serializer.validated_data["status"]
        barber.save(update_fields=["status", "updated_at"])
        return Response({
            "status": barber.status,
            "status_display": barber.get_status_display(),
            "message": "Holat muvaffaqiyatli yangilandi.",
        })


class BarberAffiliateAPIView(APIView):
    """
    Sartaroshning sartaroshxonaga birikish so'rovi yuborishi.
    """
    permission_classes = [permissions.IsAuthenticated, IsBarberSelfOrPlatformAdmin]

    def post(self, request):
        barber = get_object_or_404(Barber, user=request.user)
        serializer = BarberAffiliateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        barber.club = serializer.validated_data["club"]
        barber.branch = serializer.validated_data.get("branch")
        barber.affiliation_status = Barber.AffiliationStatus.PENDING
        barber.save(update_fields=["club", "branch", "affiliation_status", "updated_at"])

        return Response({
            "affiliation_status": barber.affiliation_status,
            "message": "Sartaroshxonaga birikish so'rovi yuborildi.",
        })
