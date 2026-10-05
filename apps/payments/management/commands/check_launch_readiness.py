from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from telegram_bot.models import TelegramBotSettings


class Command(BaseCommand):
    help = "Ishga tushirish sozlamalarini tarmoq so‘rovi yoki xabar yubormasdan tekshiradi."

    def handle(self, *args, **options):
        issues = []
        bot = TelegramBotSettings.objects.filter(pk=1).first()
        if not ((bot and bot.bot_token) or getattr(settings, "TELEGRAM_BOT_TOKEN", "")):
            issues.append("Telegram bot tokeni sozlanmagan (Django admin → Telegram bot settings).")
        if not getattr(settings, "TELEGRAM_BOT_USERNAME", ""):
            issues.append("TELEGRAM_BOT_USERNAME sozlanmagan.")
        for field in ("TELEGRAM_MINIAPP_URL", "FRONTEND_URL"):
            url = urlparse(getattr(settings, field, ""))
            if url.scheme != "https" or not url.hostname or url.hostname in {"localhost", "127.0.0.1"}:
                issues.append(f"{field} haqiqiy HTTPS domeniga sozlanmagan.")
        if settings.DEBUG:
            issues.append("DJANGO_DEBUG=true; jonli server uchun false bo‘lishi kerak.")
        if len(settings.SECRET_KEY) < 50 or settings.SECRET_KEY.startswith("django-insecure-"):
            issues.append("Jonli server uchun kuchli, maxfiy DJANGO_SECRET_KEY sozlang.")
        if not connection.features.has_select_for_update:
            issues.append("Bronlar uchun tranzaksiya qulflari kerak; jonli serverda PostgreSQL ishlating.")
        if not settings.SESSION_COOKIE_SECURE or not settings.CSRF_COOKIE_SECURE:
            issues.append("Jonli HTTPS serverda Django session va CSRF cookie secure bo‘lishi kerak.")
        if not settings.SECURE_SSL_REDIRECT:
            issues.append("DJANGO_SECURE_SSL_REDIRECT=true orqali HTTPS talab qilinsin.")
        user_model = get_user_model()
        operators = user_model.objects.filter(status=user_model.Status.ACTIVE, is_superuser=True)
        if any(user.check_password("1") for user in operators):
            issues.append("Superuser sinov paroli hali ‘1’; jonli serverdan oldin kuchli parolga almashtiring.")
        self.stdout.write("Bepul rejim har bir filial va sartarosh uchun xodim panelida belgilanadi.")
        for issue in issues:
            self.stdout.write(self.style.WARNING(issue))
        if issues:
            raise CommandError(f"Jonli ishga tushirish uchun {len(issues)} ta sozlama hali kerak.")
        self.stdout.write(self.style.SUCCESS("Ishga tushirish sozlamalari tekshirildi. Botning haqiqiy ishlashini alohida sinang."))
