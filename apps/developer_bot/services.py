import threading
import time

from django.db import DatabaseError

from apps.developer_bot.client import DeveloperTelegramClient
from apps.developer_bot.formatters import format_event
from apps.developer_bot.models import DeveloperBotSettings


_settings_lock = threading.Lock()
_cached_settings = None
_settings_cache_expires_at = 0.0


def get_developer_bot_settings():
    global _cached_settings, _settings_cache_expires_at

    if time.monotonic() < _settings_cache_expires_at:
        return _cached_settings
    with _settings_lock:
        if time.monotonic() < _settings_cache_expires_at:
            return _cached_settings
        try:
            _cached_settings = DeveloperBotSettings.objects.filter(pk=1).first()
            _settings_cache_expires_at = time.monotonic() + 30
        except DatabaseError:
            # Keep the last valid token available when the reported failure is
            # itself a temporary database outage.
            _settings_cache_expires_at = time.monotonic() + 5
        return _cached_settings


def clear_developer_bot_settings_cache():
    global _settings_cache_expires_at
    _settings_cache_expires_at = 0.0


def developer_bot_is_configured(configuration=None):
    configuration = configuration or get_developer_bot_settings()
    return bool(configuration and configuration.is_configured)


def get_developer_bot_client(configuration=None):
    configuration = configuration or get_developer_bot_settings()
    if not developer_bot_is_configured(configuration):
        raise RuntimeError("Developer bot is not configured")
    return DeveloperTelegramClient(
        token=configuration.bot_token,
        chat_id=configuration.chat_id,
        timeout=configuration.request_timeout_seconds,
    )


def notify_developer(title, message, level="INFO", category=None):
    configuration = get_developer_bot_settings()
    if not developer_bot_is_configured(configuration):
        return None
    if category and not getattr(configuration, category, False):
        return None
    return get_developer_bot_client(configuration).send_message(
        format_event(
            title,
            message,
            level=level,
            environment=configuration.environment,
        )
    )


def notify_developer_async(title, message, level="INFO", category=None):
    configuration = get_developer_bot_settings()
    if not developer_bot_is_configured(configuration):
        return
    if category and not getattr(configuration, category, False):
        return

    def send_safely():
        try:
            notify_developer(
                title,
                message,
                level=level,
                category=category,
            )
        except Exception:
            # Operational notifications must not affect the business action.
            return

    worker = threading.Thread(
        target=send_safely,
        name="developer-telegram-notification",
        daemon=True,
    )
    worker.start()
