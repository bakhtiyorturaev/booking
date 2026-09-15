import concurrent.futures
import logging

from django.conf import settings
from apps.audit.models import AuditLog


logger = logging.getLogger(__name__)
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

_audit_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="audit_logger",
)


def _should_use_async():
    # SQLite in tests/dev has file-level write locking across threads; use sync for SQLite
    engine = getattr(settings, "DATABASES", {}).get("default", {}).get("ENGINE", "")
    if "sqlite3" in engine:
        return False
    return getattr(settings, "AUDIT_ASYNC", True)


def _client_ip(request):
    remote_address = request.META.get("REMOTE_ADDR") or None
    if remote_address not in settings.TRUSTED_PROXY_IPS:
        return remote_address
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded_for.split(",", 1)[0].strip() or remote_address


def _save_audit_log(
    actor_id,
    method,
    path,
    action,
    object_id,
    status_code,
    ip_address,
    user_agent,
    request_id,
):
    try:
        AuditLog.objects.create(
            actor_id=actor_id,
            method=method,
            path=path,
            action=action,
            object_id=object_id,
            status_code=status_code,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
    except Exception:
        logger.exception("Audit yozuvini saqlab bo‘lmadi.")


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method not in MUTATING_METHODS or not request.path.startswith("/api/"):
            return response

        actor = getattr(request, "user", None)
        actor_id = getattr(actor, "pk", None) if getattr(actor, "is_authenticated", False) else None
        resolver_match = getattr(request, "resolver_match", None)
        kwargs = resolver_match.kwargs if resolver_match else {}
        action = resolver_match.view_name if resolver_match else ""
        object_id = kwargs.get("pk") or kwargs.get("id") or kwargs.get("booking_id") or ""

        ip_addr = _client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
        request_id = request.headers.get("X-Request-ID", "")[:100]

        if _should_use_async():
            _audit_executor.submit(
                _save_audit_log,
                actor_id=actor_id,
                method=request.method,
                path=request.path[:500],
                action=action[:100],
                object_id=str(object_id)[:100],
                status_code=response.status_code,
                ip_address=ip_addr,
                user_agent=user_agent,
                request_id=request_id,
            )
        else:
            _save_audit_log(
                actor_id=actor_id,
                method=request.method,
                path=request.path[:500],
                action=action[:100],
                object_id=str(object_id)[:100],
                status_code=response.status_code,
                ip_address=ip_addr,
                user_agent=user_agent,
                request_id=request_id,
            )

        return response
