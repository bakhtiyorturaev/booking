import secrets
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, UserProfile
from apps.accounts.services.auth_tokens import create_auth_tokens
from apps.accounts.utils import generate_unique_username
from telegram_bot.models import TelegramBotSettings


CACHE_PREFIX = "tg_web_login:"
TOKEN_TTL_SECONDS = 600  # 10 daqiqa


class TelegramWebLoginError(Exception):
    def __init__(self, code, detail=""):
        self.code = str(code)
        self.detail = str(detail)
        super().__init__(self.code)


def get_effective_bot_username():
    bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "").strip()
    if bot_username:
        return bot_username.lstrip("@")
    cached = cache.get("telegram_bot_me_username")
    if cached:
        return cached
    try:
        from telegram_bot.client import TelegramClient
        client = TelegramClient()
        me = client.request("getMe")
        if me and me.get("username"):
            cached = me["username"]
            cache.set("telegram_bot_me_username", cached, timeout=86400)
            return cached
    except Exception:
        pass
    return "RezervUz_bot"


def init_web_login():
    """
    Brauzer foydalanuvchisi uchun Telegram orqali kirish sessiyasini boshlash.
    """
    token = secrets.token_urlsafe(32)
    cache_key = f"{CACHE_PREFIX}{token}"
    cache.set(cache_key, {"status": "PENDING", "created_at": int(timezone.now().timestamp())}, timeout=TOKEN_TTL_SECONDS)

    bot_username = get_effective_bot_username()
    deep_link = f"https://t.me/{bot_username}?start=login_{token}"
    return {
        "token": token,
        "bot_username": bot_username,
        "deep_link": deep_link,
        "expires_in": TOKEN_TTL_SECONDS,
    }


@transaction.atomic
def confirm_web_login_from_bot(token, user_info, device_name="Web Browser via Telegram Bot", ip_address=None):
    """
    Foydalanuvchi Telegram botda /start login_<token> ni bosganda web sessiyani tasdiqlash.
    """
    cache_key = f"{CACHE_PREFIX}{token}"
    session_data = cache.get(cache_key)
    if not session_data:
        return False

    telegram_user_id = user_info.get("id")
    if not telegram_user_id:
        return False

    user = User.objects.select_for_update().filter(telegram_user_id=telegram_user_id).first()
    is_new_user = False

    first_name = user_info.get("first_name", "").strip()
    last_name = user_info.get("last_name", "").strip()
    full_name = f"{first_name} {last_name}".strip()
    tg_username = user_info.get("username", "").strip()
    language_code = user_info.get("language_code", "uz").strip().lower()

    if user is None:
        preferred_username = tg_username or f"tg_{telegram_user_id}"
        user = User.objects.create_user(
            username=generate_unique_username(preferred_username),
            telegram_user_id=telegram_user_id,
            telegram_verified_at=timezone.now(),
        )
        is_new_user = True
    else:
        if user.status != User.Status.ACTIVE:
            cache.set(cache_key, {"status": "BLOCKED"}, timeout=60)
            return False

    profile, _ = UserProfile.objects.get_or_create(user=user)
    changed = []
    if not profile.full_name and full_name:
        profile.full_name = full_name[:150]
        changed.append("full_name")
    if profile.telegram_chat_id != str(telegram_user_id):
        profile.telegram_chat_id = str(telegram_user_id)
        changed.append("telegram_chat_id")
    if language_code in {"uz", "ru", "en"} and profile.preferred_language != language_code:
        profile.preferred_language = language_code
        changed.append("preferred_language")
    if changed:
        changed.append("updated_at")
        profile.save(update_fields=changed)

    tokens = create_auth_tokens(user, device_name=device_name, ip_address=ip_address)

    cache.set(
        cache_key,
        {
            "status": "SUCCESS",
            "user_id": str(user.id),
            "tokens": tokens,
            "is_new_user": is_new_user,
        },
        timeout=300,
    )
    return True


def check_web_login_status(token):
    """
    Brauzer modalidagi polling so'rovi uchun holatni tekshirish.
    """
    cache_key = f"{CACHE_PREFIX}{token}"
    session_data = cache.get(cache_key)
    if not session_data:
        raise TelegramWebLoginError("auth.session_expired", "Login sessiyasi muddati tugagan.")

    status = session_data.get("status")
    if status == "PENDING":
        return {"status": "PENDING"}

    if status == "BLOCKED":
        cache.delete(cache_key)
        raise TelegramWebLoginError("auth.user_blocked", "Foydalanuvchi bloklangan.")

    if status == "SUCCESS":
        user_id = session_data.get("user_id")
        user = User.objects.filter(id=user_id).first()
        tokens = session_data.get("tokens")
        is_new_user = session_data.get("is_new_user", False)
        # 60 soniya davomida SUCCESS holatida qoldiramiz (race condition va qayta yuklashlar uchun)
        cache.set(cache_key, session_data, timeout=60)
        return {
            "status": "SUCCESS",
            "user": user,
            "tokens": tokens,
            "is_new_user": is_new_user,
        }

    raise TelegramWebLoginError("common.unknown_error", "Noma'lum sessiya holati.")
