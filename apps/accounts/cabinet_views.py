from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer
from apps.clubs.permissions import is_platform_admin
from apps.core.responses import error_response, success_response


class CabinetUserPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(tags=["Admin Cabinet"], summary="Foydalanuvchilar ro‘yxati"),
    retrieve=extend_schema(tags=["Admin Cabinet"], summary="Foydalanuvchi ma’lumoti"),
)
class CabinetUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    pagination_class = CabinetUserPagination
    queryset = User.objects.all().select_related("profile").order_by("-created_at")

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not is_platform_admin(request.user):
            self.permission_denied(request, message="clubs.permission_denied", code="clubs.permission_denied")

    def get_queryset(self):
        qs = super().get_queryset()
        query = self.request.query_params.get("query", "").strip()
        role = self.request.query_params.get("role", "").strip()
        user_status = self.request.query_params.get("status", "").strip()

        if query:
            qs = qs.filter(
                Q(username__icontains=query)
                | Q(phone__icontains=query)
                | Q(profile__full_name__icontains=query)
            )
        if role and role in User.Role.values:
            qs = qs.filter(role=role)
        if user_status and user_status in User.Status.values:
            qs = qs.filter(status=user_status)

        return qs

    @extend_schema(
        tags=["Admin Cabinet"],
        summary="Foydalanuvchi holatini o‘zgartirish (ACTIVE/BLOCKED)",
        request=None,
    )
    @action(detail=True, methods=["post"], url_path="toggle-status")
    def toggle_status(self, request, pk=None):
        user = self.get_object()
        if user.id == request.user.id:
            return error_response("auth.cannot_block_self", request, status_code=400)

        if user.status == User.Status.ACTIVE:
            user.status = User.Status.BLOCKED
        else:
            user.status = User.Status.ACTIVE

        user.save(update_fields=["status", "updated_at"])
        return success_response(
            "auth.status_updated",
            request,
            data=UserSerializer(user).data,
        )

    @extend_schema(
        tags=["Admin Cabinet"],
        summary="Foydalanuvchi rolini o‘zgartirish",
        request=None,
    )
    @action(detail=True, methods=["post"], url_path="set-role")
    def set_role(self, request, pk=None):
        user = self.get_object()
        new_role = request.data.get("role")
        if new_role not in User.Role.values:
            return error_response("auth.invalid_role", request, status_code=400)

        user.role = new_role
        user.is_staff = new_role in [User.Role.ADMIN, User.Role.MODERATOR]
        user.save(update_fields=["role", "is_staff", "updated_at"])
        return success_response(
            "auth.role_updated",
            request,
            data=UserSerializer(user).data,
        )
