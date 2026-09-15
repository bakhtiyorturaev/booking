import concurrent.futures
import logging

_bot_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="developer_bot_sender",
)


def _send_to_telegram(configuration, message):
    from apps.developer_bot.services import get_developer_bot_client

    try:
        get_developer_bot_client(configuration).send_message(message)
    except Exception:
        return


class TelegramErrorHandler(logging.Handler):
    """Send ERROR and CRITICAL records to the private developer group."""

    def emit(self, record):
        from apps.developer_bot.formatters import format_log_record
        from apps.developer_bot.services import (
            developer_bot_is_configured,
            get_developer_bot_settings,
        )

        try:
            configuration = get_developer_bot_settings()
            if (
                not developer_bot_is_configured(configuration)
                or not configuration.notify_errors
            ):
                return

            message = format_log_record(
                record,
                environment=configuration.environment,
            )
            if getattr(configuration, "environment", "") == "test":
                _send_to_telegram(configuration, message)
            else:
                _bot_executor.submit(_send_to_telegram, configuration, message)
        except Exception:
            # A monitoring failure must never hide or recursively log the
            # original application error or create stderr log output.
            return
