from rest_framework.permissions import BasePermission

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
