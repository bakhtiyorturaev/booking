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


def format_log_record(record, environment="development"):
    created_at = datetime.fromtimestamp(record.created, tz=timezone.utc)
    message = redact_sensitive_data(record.getMessage())
    exception = redact_sensitive_data(_exception_text(record))

    icon = "🔥" if record.levelname == "CRITICAL" else "🚨"
    parts = [
        f"{icon} <b>{html.escape(record.levelname)}</b>",
        f"<b>Muhit:</b> {html.escape(environment)}",
        f"<b>Vaqt:</b> {created_at.isoformat(timespec='seconds')}",
        f"<b>Logger:</b> {html.escape(record.name)}",
        f"<b>Xabar:</b> {_escape_with_limit(message, 1000)}",
    ]
    text = "\n".join(parts)
    if exception:
        wrapper = "\n<b>Stack trace:</b>\n<pre></pre>"
        available = TELEGRAM_MESSAGE_LIMIT - len(text) - len(wrapper)
        if available > 1:
            text += (
                "\n<b>Stack trace:</b>\n<pre>"
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
