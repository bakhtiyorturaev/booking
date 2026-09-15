from django.core.management.base import BaseCommand, CommandError

from apps.core.services.messages import get_system_message
from telegram_bot.client import TelegramClient
from telegram_bot.models import TelegramBotSettings, TelegramGroup


class Command(BaseCommand):
    help = "Telegram bot va test guruhiga ulanishni tekshiradi."

    def handle(self, *args, **options):
        configuration = TelegramBotSettings.objects.filter(pk=1).first()
        chat_id = configuration.test_group_chat_id if configuration else None
        if not chat_id:
            raise CommandError(
                "Telegram bot tokeni va test group chat ID ni admin orqali sozlang."
            )

        try:
            client = TelegramClient()
            bot = client.request("getMe")
            chat = client.request("getChat", chat_id=chat_id)
            group, _ = TelegramGroup.objects.update_or_create(
                chat_id=chat_id,
                defaults={"name": chat.get("title", "Test group"), "is_active": True},
            )
            client.send_message(
                group.chat_id,
                get_system_message("telegram.bot_connected_to_group", group.language)["message"],
                {"inline_keyboard": []},
            )
        except Exception as error:
            raise CommandError("Telegram ulanishini tekshirishda xatolik yuz berdi.") from error

        self.stdout.write(
            self.style.SUCCESS(f"@{bot['username']} → {group.name}: muvaffaqiyatli")
        )
