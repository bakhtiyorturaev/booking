from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.accounts.models import User
from apps.clubs.models import Branch, Club, ResourceBlock, Zone


def is_platform_admin(user):
    return bool(
        user
        and user.is_authenticated
        and (
            user.is_staff
            or user.is_superuser
            or user.role in {User.Role.ADMIN, User.Role.MODERATOR}
        )
    )


def club_for_object(obj):
    if isinstance(obj, Club):
        return obj
    if isinstance(obj, Branch):
        return obj.club
    if isinstance(obj, Zone):
        return obj.branch.club
    if isinstance(obj, ResourceBlock):
        return obj.zone.branch.club
    if getattr(obj, "zone_id", None):
        return obj.zone.branch.club
    if getattr(obj, "barber_id", None):
        return obj.barber.club
    if hasattr(obj, "club"):
        return obj.club
    if hasattr(obj, "branch"):
        return obj.branch.club
    return None


def can_manage_club(user, club, managers_only=False):
    if not user or not user.is_authenticated or club is None:
        return False
    return is_platform_admin(user) or club.owner_id == user.id


class IsClubOperator(BasePermission):
    message = "clubs.permission_denied"
    code = "clubs.permission_denied"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if getattr(obj, "barber_id", None) and obj.barber.user_id == request.user.pk:
            return True
        club = club_for_object(obj)
        managers_only = request.method == "DELETE"
        return can_manage_club(request.user, club, managers_only=managers_only)


class IsOwnerOrPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        club = club_for_object(obj)
        return is_platform_admin(request.user) or (
            club is not None and club.owner_id == request.user.id
        )


class IsStaffOrReadOnly(BasePermission):
    message = "Client kabineti faqat ko‘rish uchun."

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or is_platform_admin(request.user)


class IsBarberSelfOrPlatformAdmin(BasePermission):
    """Sartaroshning o'z-o'ziga xizmat endpointlari uchun.

    O'qish — har qanday autentifikatsiyalangan foydalanuvchi; yozish — faqat
    o'z `barber_profile` egasi yoki platforma admini. Ilgari bu view'larda
    `IsStaffOrReadOnly` ishlatilgani uchun sartarosh o'z holatini ham
    o'zgartira olmay 403 olardi.
    """

    message = "clubs.permission_denied"
    code = "clubs.permission_denied"

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return is_platform_admin(user) or hasattr(user, "barber_profile")


class IsClubBarberManagerOrReadOnly(BasePermission):
    """Sartaroshlar kabineti: yozish — platforma admini yoki klub egasi.

    Obyekt darajasidagi tekshiruv `CabinetBarberViewSet` ichidagi
    `require_affiliation_manager()` / `perform_update()` da bajariladi.
    """

    message = "clubs.permission_denied"
    code = "clubs.permission_denied"

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return is_platform_admin(user) or user.owned_clubs.exists()


class IsSuperuserOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(
            request.user and request.user.is_authenticated and request.user.is_superuser
        )
