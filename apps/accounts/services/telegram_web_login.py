"""Telegram bot identifikatori uchun yordamchi funksiyalar.

XAVFSIZLIK TARIXI
-----------------
Bu modulda ilgari `/start login_<token>` deep-link orqali "bir klik bilan
kirish" oqimi bo'lgan (`init_web_login` / `confirm_web_login_from_bot` /
`check_web_login_status`). U brauzer sessiyasini Telegram foydalanuvchisiga
hech qanday tarzda bog'lamagani uchun klassik **session fixation / login CSRF**
zaifligini ochib turgan:

  1. hujumchi `init_web_login()` orqali `token` oladi;
  2. `https://t.me/<bot>?start=login_<token>` havolasini qurbonga yuboradi;
  3. qurbon "Start" bosishi bilan server QURBON uchun JWT yaratib, uni
     hujumchining tokeni kalitida cache'ga yozadi;
  4. hujumchi `/auth/telegram-web/check/<token>/` ni polling qilib qurbonning
     access/refresh tokenlarini oladi — to'liq akkaunt egallash.

Oqim butunlay olib tashlandi. Uning o'rniga `apps.accounts.services.
telegram_code_auth` dagi `/start auth_<session_id>` + 5 xonali kod oqimi
ishlatiladi: kod faqat Telegramda ko'rsatiladi va uni brauzerga **foydalanuvchi
o'zi** kiritishi shart, shu bilan sessiya haqiqiy egasiga bog'lanadi.
Frontend (`components/auth/TelegramAuthModal.vue`) allaqachon faqat shu
xavfsiz oqimni ishlatadi.
"""

from django.conf import settings
from django.core.cache import cache

BOT_USERNAME_CACHE_KEY = "telegram_bot_me_username"
BOT_USERNAME_CACHE_TTL = 86400
FALLBACK_BOT_USERNAME = "RezervUz_bot"


class TelegramWebLoginError(Exception):
    def __init__(self, code, detail=""):
        self.code = str(code)
        self.detail = str(detail)
        super().__init__(self.code)


def get_effective_bot_username(strict=False):
    """Bot username'ini sozlamadan, keyin Telegram `getMe` dan aniqlaydi."""
    bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "").strip()
    if bot_username:
        return bot_username.lstrip("@")

    cached = cache.get(BOT_USERNAME_CACHE_KEY)
    if cached:
        return cached

    try:
        from telegram_bot.client import TelegramClient

        me = TelegramClient().request("getMe")
        if me and me.get("username"):
            cache.set(BOT_USERNAME_CACHE_KEY, me["username"], timeout=BOT_USERNAME_CACHE_TTL)
            return me["username"]
    except Exception:
        pass

    if strict:
        raise TelegramWebLoginError(
            "auth.telegram_not_configured", "Telegram bot username sozlanmagan."
        )
    return FALLBACK_BOT_USERNAME
