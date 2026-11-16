import concurrent.futures
import logging
import threading

_bot_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="developer_bot_sender",
)
# `ThreadPoolExecutor`ning ichki navbati cheksiz — xatoliklar "to'lqini"
# paytida (masalan, tashqi xizmat ishlamay qolganda) minglab ERROR
# yozuvlari bir zumda navbatga tushib, xotirani cheksiz o'stirishi mumkin.
# Bu — faqat monitoring signali, shuning uchun navbat to'lib ketganda
# yangi bildirishnomalarni jim tashlab yuboramiz (sinxron yuborish xato
# qaytadan logga yozilib, rekursiyaga olib kelishi mumkin).
_bot_queue_capacity = threading.BoundedSemaphore(50)


def _send_to_telegram(configuration, message):
    from apps.core.developer_bot.services import get_developer_bot_client

    try:
        get_developer_bot_client(configuration).send_message(message)
    except Exception:
        return


def _submit_to_telegram(configuration, message):
    if not _bot_queue_capacity.acquire(blocking=False):
        return

    def _run():
        try:
            _send_to_telegram(configuration, message)
        finally:
            _bot_queue_capacity.release()

    _bot_executor.submit(_run)


class TelegramErrorHandler(logging.Handler):
    """Send ERROR and CRITICAL records to the private developer group."""

    def emit(self, record):
        from apps.core.developer_bot.formatters import format_log_record
        from apps.core.developer_bot.services import (
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
                _submit_to_telegram(configuration, message)
        except Exception:
            # A monitoring failure must never hide or recursively log the
            # original application error or create stderr log output.
            return
