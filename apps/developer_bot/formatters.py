import html
import re
import traceback
from datetime import datetime, timezone

TELEGRAM_MESSAGE_LIMIT = 4096
REDACTED = "[REDACTED]"
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*)([^\s,;]+(?:\s+[^\s,;]+)?)"),
    re.compile(
        r"(?i)((?:access|refresh|api|auth|bot)?_?token|secret|password|passwd|otp)"
        r"(\s*[:=]\s*)"
        r"([^\s,;}&]+)"
    ),
    re.compile(r"(?i)(bearer\s+)[a-z0-9._~+/=-]+"),
)


def redact_sensitive_data(value):
    text = str(value)
    for pattern in SENSITIVE_VALUE_PATTERNS:
        if pattern.groups >= 3:
            text = pattern.sub(rf"\1\2{REDACTED}", text)
        else:
            text = pattern.sub(rf"\1{REDACTED}", text)
    return text


def _exception_text(record):
    if not record.exc_info:
        return ""
    return "".join(traceback.format_exception(*record.exc_info)).strip()


def _escape_with_limit(value, max_length):
    value = str(value)
    escaped = html.escape(value)
    if len(escaped) <= max_length:
        return escaped

    suffix = "…"
    low, high = 0, len(value)
    while low < high:
        middle = (low + high + 1) // 2
        if len(html.escape(value[:middle])) + len(suffix) <= max_length:
            low = middle
        else:
            high = middle - 1
    return html.escape(value[:low]) + suffix


try:
    from zoneinfo import ZoneInfo
    TASHKENT_TZ = ZoneInfo("Asia/Tashkent")
except Exception:
    from datetime import timedelta
    TASHKENT_TZ = timezone(timedelta(hours=5))


def _format_request_details(request):
    if not request:
        return []
    try:
        method = getattr(request, "method", "UNKNOWN")
        path = getattr(request, "path", "")
        full_path = request.get_full_path() if hasattr(request, "get_full_path") else path

        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            user_str = f"{getattr(user, 'username', 'user')} (ID: {getattr(user, 'pk', '-')}, Rol: {getattr(user, 'role', '-')})"
        else:
            user_str = "Anonymous (Tizimga kirmagan)"

        x_forwarded = getattr(request, "META", {}).get("HTTP_X_FORWARDED_FOR", "")
        client_ip = x_forwarded.split(",")[0].strip() if x_forwarded else getattr(request, "META", {}).get("REMOTE_ADDR", "-")

        lines = [
            f"<b>Endpoint:</b> <code>{html.escape(method)} {html.escape(full_path)}</code>",
            f"<b>Foydalanuvchi:</b> {html.escape(user_str)}",
            f"<b>Client IP:</b> <code>{html.escape(client_ip)}</code>",
        ]

        if hasattr(request, "GET") and request.GET:
            params = redact_sensitive_data(str(request.GET.dict()))
            lines.append(f"<b>Query params:</b> <code>{html.escape(params)}</code>")

        if method in ("POST", "PATCH", "PUT") and hasattr(request, "body"):
            try:
                body_bytes = getattr(request, "body", b"")
                if body_bytes:
                    body_str = body_bytes.decode("utf-8", errors="ignore").strip()
                    if body_str:
                        redacted_body = redact_sensitive_data(body_str)
                        lines.append(f"<b>Request body:</b> <code>{_escape_with_limit(redacted_body, 400)}</code>")
            except Exception:
                pass

        return lines
    except Exception:
        return []


def format_log_record(record, environment="development"):
    created_at = datetime.fromtimestamp(record.created, tz=TASHKENT_TZ)
    formatted_time = created_at.strftime("%Y-%m-%d %H:%M:%S (Toshkent vaqti)")
    message = redact_sensitive_data(record.getMessage())
    exception = redact_sensitive_data(_exception_text(record))

    icon = "🔥" if record.levelname == "CRITICAL" else "🚨"
    parts = [
        f"{icon} <b>{html.escape(record.levelname)}</b>",
        f"<b>Muhit:</b> {html.escape(environment)}",
        f"<b>Vaqt:</b> {formatted_time}",
        f"<b>Logger:</b> {html.escape(record.name)}",
    ]

    request = getattr(record, "request", None)
    req_details = _format_request_details(request)
    if req_details:
        parts.extend(req_details)

    parts.append(f"<b>Xabar:</b> {_escape_with_limit(message, 1000)}")

    text = "\n".join(parts)
    if exception:
        wrapper = "\n\n<b>Stack trace:</b>\n<pre></pre>"
        available = TELEGRAM_MESSAGE_LIMIT - len(text) - len(wrapper)
        if available > 1:
            text += (
                "\n\n<b>Stack trace:</b>\n<pre>"
                f"{_escape_with_limit(exception, available)}</pre>"
            )
    return text[:TELEGRAM_MESSAGE_LIMIT]


def format_event(title, message, level="INFO", environment="development"):
    safe_title = _escape_with_limit(redact_sensitive_data(title), 200)
    prefix = (
        f"ℹ️ <b>{html.escape(level.upper())}: {safe_title}</b>\n"
        f"<b>Muhit:</b> {html.escape(environment)}\n"
        "<b>Xabar:</b> "
    )
    safe_message = _escape_with_limit(
        redact_sensitive_data(message),
        TELEGRAM_MESSAGE_LIMIT - len(prefix),
    )
    return prefix + safe_message
