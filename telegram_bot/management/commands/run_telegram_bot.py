import logging
import time

from django.core.management.base import BaseCommand

from telegram_bot.client import TelegramClient
from telegram_bot.handlers import handle_callback, handle_message
from telegram_bot.models import TelegramBotSettings
from telegram_bot.services import dispatch_pending_messages
from apps.bookings.services import process_booking_lifecycle


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Telegram botni long polling rejimida ishga tushiradi."

    def handle(self, *args, **options):
        client = TelegramClient()
        offset = None
        self.stdout.write(self.style.SUCCESS("Telegram bot ishga tushdi."))
        while True:
            try:
                try:
                    process_booking_lifecycle()
                except Exception as lifecycle_err:
                    logger.warning("Booking lifecycle error: %s", lifecycle_err)

                try:
                    dispatch_pending_messages(client)
                except Exception as dispatch_err:
                    logger.warning("Pending message dispatch error: %s", dispatch_err)

                for update in client.get_updates(offset=offset):
                    offset = update["update_id"] + 1
                    if callback := update.get("callback_query"):
                        handle_callback(client, callback)
                    elif message := update.get("message"):
                        handle_message(client, message)
            except KeyboardInterrupt:
                return
            except Exception:
                logger.exception("Telegram polling jarayonida xatolik yuz berdi.")
                configuration = TelegramBotSettings.objects.filter(pk=1).first()
                time.sleep(
                    configuration.retry_delay_seconds if configuration else 5
                )
