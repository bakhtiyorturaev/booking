from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.barbers.models import Barber
from apps.barbers.serializers import CabinetBarberSerializer
from apps.clubs.permissions import is_platform_admin


class IsPlatformStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and is_platform_admin(request.user)


class CabinetBarberViewSet(viewsets.ModelViewSet):
    """
    Xodimlar admin paneli uchun sartaroshlarni boshqarish va arizalarni tasdiqlash.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CabinetBarberSerializer
    queryset = Barber.objects.all().select_related("user", "club", "branch").order_by("-created_at")

    def get_queryset(self):
        qs = super().get_queryset()
        if not is_platform_admin(self.request.user):
            qs = qs.filter(Q(user=self.request.user) | Q(club__owner=self.request.user))
        affiliation = self.request.query_params.get("affiliation_status")
        club_id = self.request.query_params.get("club_id")
        query = self.request.query_params.get("query") or self.request.query_params.get("search")

        if affiliation:
            qs = qs.filter(affiliation_status=affiliation)
        if club_id:
            qs = qs.filter(club_id=club_id)
        if query:
            qs = qs.filter(full_name__icontains=query)

        return qs

    def perform_create(self, serializer):
        if not is_platform_admin(self.request.user):
            self.permission_denied(self.request)
        serializer.save()

    def perform_update(self, serializer):
        if not is_platform_admin(self.request.user):
            for field in ("user", "club", "branch", "billing_city", "billing_district", "affiliation_status", "is_active"):
                if field in serializer.validated_data and serializer.validated_data[field] != getattr(serializer.instance, field):
                    self.permission_denied(self.request)
        serializer.save()

    def perform_destroy(self, instance):
        if not is_platform_admin(self.request.user):
            self.permission_denied(self.request)
        instance.is_active = False
        instance.save(update_fields=("is_active", "updated_at"))

    def require_affiliation_manager(self, barber):
        if not is_platform_admin(self.request.user) and (barber.club_id is None or barber.club.owner_id != self.request.user.pk):
            self.permission_denied(self.request)

    @action(detail=True, methods=["post"], url_path="approve-affiliation")
    def approve_affiliation(self, request, pk=None):
        barber = self.get_object()
        self.require_affiliation_manager(barber)
        barber.affiliation_status = Barber.AffiliationStatus.APPROVED
        barber.save(update_fields=["affiliation_status", "updated_at"])
        return Response({
            "affiliation_status": barber.affiliation_status,
            "message": "Sartaroshxonaga birikish tasdiqlandi.",
        })

    @action(detail=True, methods=["post"], url_path="reject-affiliation")
    def reject_affiliation(self, request, pk=None):
        barber = self.get_object()
        self.require_affiliation_manager(barber)
        barber.affiliation_status = Barber.AffiliationStatus.REJECTED
        barber.save(update_fields=["affiliation_status", "updated_at"])
        return Response({
            "affiliation_status": barber.affiliation_status,
            "message": "Birikish arizasi rad etildi.",
        })

    @action(detail=True, methods=["post"], url_path="toggle-status")
    def toggle_status(self, request, pk=None):
        barber = self.get_object()
        if not is_platform_admin(request.user):
            self.permission_denied(request)
        barber.is_active = not barber.is_active
        barber.save(update_fields=["is_active", "updated_at"])
        return Response({
            "is_active": barber.is_active,
            "message": f"Sartarosh holati: {'Faol' if barber.is_active else 'Nofaol'}.",
        })
