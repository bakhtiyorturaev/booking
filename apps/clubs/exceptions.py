import re

from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler

from apps.accounts.models import UserProfile
from apps.core.models import normalize_language
from apps.core.services.messages import get_system_message


MESSAGE_CODE_PATTERN = re.compile(r"^[a-z0-9_]+(?:\.[a-z0-9_]+)+$")


def _localized_app(context):
    view = context.get("view")
    module = view.__class__.__module__ if view else ""
    for app in ("clubs", "bookings", "reviews", "payments", "accounts"):
        if module.startswith(f"apps.{app}."):
            return app
    return None


def _request_language(request):
    query_language = request.query_params.get("lang")
    if query_language:
        return normalize_language(query_language)

    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        try:
            return normalize_language(user.profile.preferred_language)
        except UserProfile.DoesNotExist:
            pass

    return normalize_language(request.headers.get("Accept-Language", "uz"))


def _first_message_code(value):
    if isinstance(value, dict):
        for item in value.values():
            code = _first_message_code(item)
            if code:
                return code
        return None

    if isinstance(value, (list, tuple)):
        for item in value:
            code = _first_message_code(item)
            if code:
                return code
        return None

    text = str(value)
    if MESSAGE_CODE_PATTERN.fullmatch(text):
        return text

    detail_code = str(getattr(value, "code", ""))
    if MESSAGE_CODE_PATTERN.fullmatch(detail_code):
        return detail_code

    return None


def _fallback_code(http_status, app):
    if http_status == status.HTTP_401_UNAUTHORIZED:
        return "auth.unauthorized"
    if app == "bookings":
        if http_status == status.HTTP_403_FORBIDDEN:
            return "bookings.permission_denied"
        if http_status == status.HTTP_404_NOT_FOUND:
            return "bookings.not_found"
        return "bookings.invalid_data"
    if app == "reviews":
        if http_status == status.HTTP_404_NOT_FOUND:
            return "reviews.not_found"
        return "reviews.invalid_data"
    if app == "payments":
        if http_status == status.HTTP_403_FORBIDDEN:
            return "payments.permission_denied"
        if http_status == status.HTTP_404_NOT_FOUND:
            return "payments.transaction_not_found"
        return "payments.invalid_status"
    if app == "accounts":
        if http_status == status.HTTP_403_FORBIDDEN:
            return "auth.unauthorized"
        if http_status == status.HTTP_404_NOT_FOUND:
            return "auth.user_not_found"
        return "common.error"
    if http_status == status.HTTP_403_FORBIDDEN:
        return "clubs.permission_denied"
    if http_status == status.HTTP_404_NOT_FOUND:
        return "clubs.not_found"
    return "clubs.invalid_data"


def _error_codes(value, fallback):
    if isinstance(value, dict):
        return {
            key: _error_codes(item, fallback)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_error_codes(item, fallback) for item in value]

    code = _first_message_code(value)
    return code or fallback


def localized_api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    app = _localized_app(context)
    if response is None or not app:
        return response

    code = _first_message_code(response.data)
    if code is None:
        code = _fallback_code(response.status_code, app)

    request = context["request"]
    message_data = get_system_message(
        code=code,
        language=_request_language(request),
    )
    response.data = {
        "success": False,
        "code": message_data["code"],
        "message": message_data["message"],
        "errors": _error_codes(response.data, code),
    }
    return response
