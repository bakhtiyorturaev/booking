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
    permission_classes = [IsPlatformStaff]
    serializer_class = CabinetBarberSerializer
    queryset = Barber.objects.all().select_related("user", "club", "branch").order_by("-created_at")

    def get_queryset(self):
        qs = super().get_queryset()
        affiliation = self.request.query_params.get("affiliation_status")
        club_id = self.request.query_params.get("club_id")
        query = self.request.query_params.get("query")

        if affiliation:
            qs = qs.filter(affiliation_status=affiliation)
        if club_id:
            qs = qs.filter(club_id=club_id)
        if query:
            qs = qs.filter(full_name__icontains=query)

        return qs

    @action(detail=True, methods=["post"], url_path="approve-affiliation")
    def approve_affiliation(self, request, pk=None):
        barber = self.get_object()
        barber.affiliation_status = Barber.AffiliationStatus.APPROVED
        barber.save(update_fields=["affiliation_status", "updated_at"])
        return Response({
            "affiliation_status": barber.affiliation_status,
            "message": "Sartaroshxonaga birikish tasdiqlandi.",
        })

    @action(detail=True, methods=["post"], url_path="reject-affiliation")
    def reject_affiliation(self, request, pk=None):
        barber = self.get_object()
        barber.affiliation_status = Barber.AffiliationStatus.REJECTED
        barber.save(update_fields=["affiliation_status", "updated_at"])
        return Response({
            "affiliation_status": barber.affiliation_status,
            "message": "Birikish arizasi rad etildi.",
        })

    @action(detail=True, methods=["post"], url_path="toggle-status")
    def toggle_status(self, request, pk=None):
        barber = self.get_object()
        barber.is_active = not barber.is_active
        barber.save(update_fields=["is_active", "updated_at"])
        return Response({
            "is_active": barber.is_active,
            "message": f"Sartarosh holati: {'Faol' if barber.is_active else 'Nofaol'}.",
        })
