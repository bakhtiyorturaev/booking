import logging
import time

from django.core.management.base import BaseCommand
from requests.exceptions import ConnectionError as TelegramConnectionError, Timeout as TelegramTimeout

from telegram_bot.client import TelegramClient
from telegram_bot.handlers import handle_callback, handle_message
from telegram_bot.models import TelegramBotSettings
from telegram_bot.services import dispatch_pending_messages
from apps.bookings.services import process_booking_lifecycle


logger = logging.getLogger(__name__)
NETWORK_OUTAGE_ALERT_AFTER_SECONDS = 60
NETWORK_OUTAGE_ALERT_INTERVAL_SECONDS = 30 * 60


class Command(BaseCommand):
    help = "Telegram botni long polling rejimida ishga tushiradi."

    def handle(self, *args, **options):
        client = TelegramClient()
        offset = None
        outage_started_at = None
        last_outage_alert_at = None
        self.stdout.write(self.style.SUCCESS("Telegram bot ishga tushdi."))
        while True:
            try:
                try:
                    process_booking_lifecycle()
                except Exception as lifecycle_err:
                    logger.warning("Booking lifecycle error: %s", lifecycle_err)

                try:
                    dispatch_pending_messages(client)
                except (TelegramConnectionError, TelegramTimeout):
                    pass
                except Exception as dispatch_err:
                    logger.warning("Pending message dispatch error: %s", dispatch_err)

                updates = client.get_updates(offset=offset)
                if outage_started_at is not None:
                    logger.info("Telegram API bilan aloqa tiklandi.")
                    outage_started_at = None
                    last_outage_alert_at = None

                for update in updates:
                    offset = update["update_id"] + 1
                    if callback := update.get("callback_query"):
                        handle_callback(client, callback)
                    elif message := update.get("message"):
                        handle_message(client, message)
            except KeyboardInterrupt:
                return
            except (TelegramConnectionError, TelegramTimeout):
                now = time.monotonic()
                if outage_started_at is None:
                    outage_started_at = now
                if (
                    now - outage_started_at >= NETWORK_OUTAGE_ALERT_AFTER_SECONDS
                    and (
                        last_outage_alert_at is None
                        or now - last_outage_alert_at >= NETWORK_OUTAGE_ALERT_INTERVAL_SECONDS
                    )
                ):
                    logger.error(
                        "Telegram API bilan aloqa uzilgan; bot qayta ulanishga urinmoqda."
                    )
                    last_outage_alert_at = now
                configuration = TelegramBotSettings.objects.filter(pk=1).first()
                time.sleep(configuration.retry_delay_seconds if configuration else 5)
            except Exception:
                logger.exception("Telegram polling jarayonida xatolik yuz berdi.")
                configuration = TelegramBotSettings.objects.filter(pk=1).first()
                time.sleep(
                    configuration.retry_delay_seconds if configuration else 5
                )
