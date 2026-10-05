from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import UserProfile
from apps.accounts.serializers import (
    AuthUserSerializer,
    ChangePasswordSerializer,
    RefreshTokenSerializer,
    StaffPasswordLoginSerializer,
    TelegramCodeExchangeSerializer,
    TelegramCodeVerifySerializer,
    TelegramContactSerializer,
    TelegramMiniAppLoginSerializer,
    UserSerializer,
    UserProfileUpdateSerializer,
)
from apps.accounts.services.auth_tokens import (
    AuthTokenError,
    public_auth_tokens,
    refresh_auth_tokens,
    revoke_user_session,
)
from apps.accounts.services.telegram_code_auth import (
    TelegramCodeAuthError,
    init_telegram_code_session,
    telegram_code_session_status,
    verify_telegram_code,
)
from apps.accounts.services.password_auth import (
    PasswordAuthError,
    change_user_password,
    login_with_password,
)
from apps.accounts.services.telegram_auth import (
    TelegramAuthError,
    get_login_settings,
    login_with_telegram,
)
from apps.accounts.services.telegram_miniapp import (
    TelegramMiniAppError,
    login_with_telegram_miniapp,
    save_telegram_contact,
)
from apps.accounts.services.telegram_web_login import (
    TelegramWebLoginError,
    check_web_login_status,
    init_web_login,
)
from apps.core.responses import (
    serializer_error_response,
    service_error_response,
    success_response,
)
from apps.accounts.utils import get_client_ip


class TelegramMiniAppLoginAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "telegram_login"

    @extend_schema(
        tags=["Authentication"],
        summary="Telegram Mini App (WebApp) orqali avto-login",
        request=TelegramMiniAppLoginSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = TelegramMiniAppLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer, request)
        try:
            result = login_with_telegram_miniapp(
                init_data_str=serializer.validated_data["init_data"],
                device_name=serializer.validated_data.get("device_name", ""),
                ip_address=get_client_ip(request),
            )
        except (TelegramMiniAppError, AuthTokenError) as error:
            return service_error_response(error, request)

        return success_response(
            "auth.login_success",
            request,
            data={
                "user": AuthUserSerializer(result["user"]).data,
                "tokens": public_auth_tokens(result["tokens"]),
                "is_new_user": result["is_new_user"],
            },
        )


class TelegramContactAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Telegram orqali olingan telefon raqamni saqlash",
        request=TelegramContactSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = TelegramContactSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer, request)
        try:
            user = save_telegram_contact(
                user=request.user,
                phone_number=serializer.validated_data["phone"],
            )
        except TelegramMiniAppError as error:
            return service_error_response(error, request)

        return success_response(
            "auth.phone_verified_success",
            request,
            data={
                "phone": user.phone,
                "is_phone_verified": user.is_phone_verified,
                "user": AuthUserSerializer(user).data,
            },
        )


class TelegramWebLoginInitAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Web brauzer uchun Telegram login sessiyasini boshlash",
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        result = init_web_login()
        return success_response("auth.google_config_loaded", request, data=result)


class TelegramWebLoginCheckAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Web brauzer Telegram login sessiyasini tekshirish",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, token):
        try:
            result = check_web_login_status(token)
        except TelegramWebLoginError as error:
            return service_error_response(error, request)

        if result.get("status") == "PENDING":
            return Response({"success": True, "data": {"status": "PENDING"}}, status=status.HTTP_200_OK)

        return success_response(
            "auth.login_success",
            request,
            data={
                "status": "SUCCESS",
                "user": AuthUserSerializer(result["user"]).data,
                "tokens": public_auth_tokens(result["tokens"]),
                "is_new_user": result["is_new_user"],
            },
        )


class TelegramAuthConfigAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            configuration = get_login_settings()
        except TelegramAuthError as error:
            return service_error_response(error, request)
        return success_response(
            "auth.google_config_loaded", request, data={"client_id": str(configuration.login_client_id)}
        )


class TelegramLoginAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "telegram_login"

    def post(self, request):
        serializer = TelegramCodeExchangeSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer, request)
        try:
            result = login_with_telegram(
                **serializer.validated_data,
                ip_address=get_client_ip(request),
            )
        except (TelegramAuthError, AuthTokenError) as error:
            return service_error_response(error, request)
        return success_response(
            "auth.login_success",
            request,
            data={
                "user": AuthUserSerializer(result["user"]).data,
                "tokens": public_auth_tokens(result["tokens"]),
                "is_new_user": result["is_new_user"],
            },
        )


class CurrentUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Profile"],
        summary="Joriy foydalanuvchini olish",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        UserProfile.objects.get_or_create(user=request.user)
        return Response(
            {
                "success": True,
                "data": {"user": UserSerializer(request.user).data},
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Profile"],
        summary="Joriy foydalanuvchi profilini yangilash",
        request=UserProfileUpdateSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def patch(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if not serializer.is_valid():
            return serializer_error_response(serializer, request)

        serializer.save()
        request.user.refresh_from_db()
        return success_response(
            message_code="auth.profile_updated_success",
            request=request,
            data={"user": UserSerializer(request.user).data},
        )


class TokenRefreshAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_refresh"

    @extend_schema(
        tags=["Authentication"],
        summary="Access tokenni yangilash",
        request=RefreshTokenSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer, request)

        try:
            tokens = refresh_auth_tokens(raw_refresh_token=serializer.validated_data["refresh"])
        except AuthTokenError as error:
            return service_error_response(error, request)

        return success_response(
            message_code="auth.tokens_refreshed_success",
            request=request,
            data={"tokens": public_auth_tokens(tokens)},
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Joriy sessiyadan chiqish",
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        session_id = request.auth.get("session_id")
        try:
            revoke_user_session(user=request.user, session_id=session_id)
        except AuthTokenError as error:
            return service_error_response(error, request)

        return success_response(message_code="auth.logout_success", request=request)


class StaffPasswordLoginAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "telegram_login"

    @extend_schema(
        tags=["Authentication"],
        summary="Xodimlar va operatorlar uchun login/parol orqali kirish (JWT)",
        request=StaffPasswordLoginSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = StaffPasswordLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer, request)

        try:
            result = login_with_password(
                login=serializer.validated_data["login"],
                password=serializer.validated_data["password"],
                device_name=serializer.validated_data.get("device_name", ""),
                ip_address=get_client_ip(request),
                login_type=serializer.validated_data.get("login_type", ""),
            )
        except (PasswordAuthError, AuthTokenError) as error:
            return service_error_response(error, request)

        return success_response(
            "auth.login_success",
            request,
            data={
                "user": AuthUserSerializer(result["user"]).data,
                "tokens": public_auth_tokens(result["tokens"]),
                "password_expired": result["password_expired"],
                "is_new_user": False,
            },
        )


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Parolni o'zgartirish (har 1 oyda talab qilinadi)",
        request=ChangePasswordSerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer, request)

        try:
            result = change_user_password(
                user=request.user,
                old_password=serializer.validated_data["old_password"],
                new_password=serializer.validated_data["new_password"],
                device_name=request.META.get("HTTP_USER_AGENT", "")[:120],
                ip_address=get_client_ip(request),
            )
        except (PasswordAuthError, AuthTokenError) as error:
            return service_error_response(error, request)

        return success_response(
            "auth.password_changed_success",
            request,
            data={
                "user": AuthUserSerializer(result["user"]).data,
                "tokens": public_auth_tokens(result["tokens"]),
                "password_expired": False,
            },
        )


class TelegramCodeInitAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "telegram_login"

    @extend_schema(
        tags=["Authentication"],
        summary="Telegram 5-talik kod orqali kirish sessiyasini boshlash",
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        try:
            data = init_telegram_code_session()
        except TelegramCodeAuthError as error:
            return service_error_response(error, request)
        return success_response("auth.code_session_started", request, data=data)


class TelegramCodeStatusAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "telegram_code_status"

    @extend_schema(tags=["Authentication"], request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        session_id = request.data.get("session_id")
        if not isinstance(session_id, str) or not 20 <= len(session_id) <= 128:
            return success_response("auth.code_session_status", request, data={"status": "expired", "expires_in": 0})
        return success_response("auth.code_session_status", request, data=telegram_code_session_status(session_id))


class TelegramCodeVerifyAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "telegram_login"

    @extend_schema(
        tags=["Authentication"],
        summary="Telegramdan olingan 5-talik kodni tasdiqlash va kirish",
        request=TelegramCodeVerifySerializer,
        responses={200: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = TelegramCodeVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return serializer_error_response(serializer, request)

        try:
            result = verify_telegram_code(
                code=serializer.validated_data["code"],
                session_id=serializer.validated_data.get("session_id"),
                device_name=serializer.validated_data.get("device_name", "") or request.META.get("HTTP_USER_AGENT", "")[:120],
                ip_address=get_client_ip(request),
            )
        except (TelegramCodeAuthError, AuthTokenError) as error:
            return service_error_response(error, request)

        return success_response(
            "auth.login_success",
            request,
            data={
                "user": AuthUserSerializer(result["user"]).data,
                "tokens": public_auth_tokens(result["tokens"]),
                "is_new_user": result["is_new_user"],
            },
        )
