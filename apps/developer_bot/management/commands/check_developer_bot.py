from django.core.management.base import BaseCommand, CommandError

from apps.developer_bot.services import (
    developer_bot_is_configured,
    get_developer_bot_client,
    notify_developer,
)


class Command(BaseCommand):
    help = "Developer Telegram bot va guruh konfiguratsiyasini tekshiradi."

    def handle(self, *args, **options):
        if not developer_bot_is_configured():
            raise CommandError(
                "Developer bot sozlamalarini Django admin orqali kiriting."
            )

        try:
            client = get_developer_bot_client()
            bot = client.get_me()
            chat = client.get_chat()
            notify_developer(
                "Monitoring ulandi",
                "Club Booking developer bot muvaffaqiyatli ishga tushdi.",
            )
        except Exception as error:
            raise CommandError(
                "Developer Telegram bot ulanishida xatolik yuz berdi."
            ) from error

        self.stdout.write(
            self.style.SUCCESS(
                f"@{bot['username']} → {chat.get('title', chat['id'])}: muvaffaqiyatli"
            )
        )
