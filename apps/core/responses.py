from rest_framework import status
from rest_framework.response import Response
from apps.core.services.messages import get_system_message
from apps.core.models import normalize_language


def get_request_language(request):
    if not request:
        return "uz"
    accept_lang = getattr(request, "headers", {}).get("Accept-Language", "uz") or "uz"
    return normalize_language(accept_lang[:2])


def success_response(message_code="common.success", request=None, data=None, http_status=status.HTTP_200_OK):
    language = get_request_language(request)
    msg = get_system_message(message_code, language)
    payload = {
        "success": True,
        "code": msg["code"],
        "message": msg["message"],
    }
    if data is not None:
        payload["data"] = data
    return Response(payload, status=http_status)


def service_error_response(error, request=None, http_status=status.HTTP_400_BAD_REQUEST):
    code = getattr(error, "code", "common.error")
    language = get_request_language(request)
    msg = get_system_message(code, language)
    return Response(
        {
            "success": False,
            "code": msg["code"],
            "message": msg["message"],
            "detail": getattr(error, "detail", ""),
        },
        status=http_status,
    )


def error_response(message_code="common.error", request=None, http_status=status.HTTP_400_BAD_REQUEST, status_code=None, detail=""):
    language = get_request_language(request)
    msg = get_system_message(message_code, language)
    effective_status = status_code or http_status
    return Response(
        {
            "success": False,
            "code": msg["code"],
            "message": msg["message"],
            "detail": detail,
        },
        status=effective_status,
    )


def serializer_error_response(serializer, request=None, http_status=status.HTTP_400_BAD_REQUEST):
    language = get_request_language(request)
    first_error_code = "common.error"
    errors = serializer.errors
    for field_errors in errors.values():
        if isinstance(field_errors, list) and field_errors:
            first_error_code = str(field_errors[0])
            break
        elif isinstance(field_errors, str):
            first_error_code = str(field_errors)
            break
    msg = get_system_message(first_error_code, language)
    return Response(
        {
            "success": False,
            "code": msg["code"],
            "message": msg["message"],
            "errors": errors,
        },
        status=http_status,
    )



