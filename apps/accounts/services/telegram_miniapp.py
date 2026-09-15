import hashlib
import hmac
import json
import secrets
import time
import urllib.parse
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, UserProfile
from apps.accounts.services.auth_tokens import create_auth_tokens
from apps.accounts.utils import generate_unique_username
from telegram_bot.models import TelegramBotSettings


class TelegramMiniAppError(Exception):
    def __init__(self, code, detail=""):
        self.code = str(code)
        self.detail = str(detail)
        super().__init__(self.code)


def get_bot_token():
    bot_settings = TelegramBotSettings.objects.filter(pk=1).first()
    token = (bot_settings.bot_token if bot_settings and bot_settings.bot_token else "") or getattr(
        settings, "TELEGRAM_BOT_TOKEN", ""
    )
    if not token:
        raise TelegramMiniAppError("auth.telegram_not_configured", "Telegram bot token sozlanmagan.")
    return token


def verify_telegram_webapp_init_data(init_data_str, bot_token=None, max_age_seconds=86400):
    """
    Telegram WebApp initData ni rasmiy Telegram xavfsizlik standarti (HMAC-SHA256)
    bo'yicha tekshiradi.
    """
    if not init_data_str:
        raise TelegramMiniAppError("auth.telegram_phone_permission_required", "initData bo‘sh.")

    bot_token = bot_token or get_bot_token()

    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data_str, keep_blank_values=True))
    except Exception as error:
        raise TelegramMiniAppError("auth.telegram_data_invalid", f"initData format xatosi: {error}") from error

    received_hash = parsed_data.pop("hash", None)
    if not received_hash:
        raise TelegramMiniAppError("auth.telegram_phone_permission_required", "Hash topilmadi.")

    auth_date_str = parsed_data.get("auth_date")
    if not auth_date_str:
        raise TelegramMiniAppError("auth.telegram_phone_permission_required", "auth_date topilmadi.")

    try:
        auth_date = int(auth_date_str)
    except (ValueError, TypeError) as error:
        raise TelegramMiniAppError("auth.telegram_data_invalid", "auth_date noto‘g‘ri formatda.") from error

    now = int(time.time())
    if max_age_seconds and (now - auth_date > max_age_seconds or auth_date > now + 300):
        raise TelegramMiniAppError("auth.telegram_data_invalid", "initData muddati o‘tgan.")

    # Kalitlarni alifbo tartibida saralab data_check_string hosil qilish
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))

    # Secret key = HMAC_SHA256("WebAppData", bot_token)
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()

    # Computed hash = HMAC_SHA256(secret_key, data_check_string)
    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not secrets.compare_digest(computed_hash, received_hash):
        raise TelegramMiniAppError("auth.telegram_data_invalid", "Imzo mos kelmadi.")

    user_raw = parsed_data.get("user")
    user_data = {}
    if user_raw:
        try:
            user_data = json.loads(user_raw)
        except Exception as error:
            raise TelegramMiniAppError("auth.telegram_data_invalid", f"User JSON xatosi: {error}") from error

    parsed_data["user_data"] = user_data
    return parsed_data


@transaction.atomic
def login_with_telegram_miniapp(init_data_str, device_name="", ip_address=None, bot_token=None):
    """
    Telegram Mini App orqali 0-click avto-login qilish.
    Foydalanuvchi mavjud bo‘lsa tizimga kiritadi, bo‘lmasa yangi User yaratadi.
    """
    validated_data = verify_telegram_webapp_init_data(init_data_str, bot_token=bot_token)
    user_info = validated_data.get("user_data") or {}

    telegram_user_id = user_info.get("id")
    if not telegram_user_id:
        raise TelegramMiniAppError("auth.telegram_phone_permission_required", "Telegram user ID topilmadi.")

    user = User.objects.select_for_update().filter(telegram_user_id=telegram_user_id).first()
    is_new_user = False

    first_name = user_info.get("first_name", "").strip()
    last_name = user_info.get("last_name", "").strip()
    full_name = f"{first_name} {last_name}".strip()
    tg_username = user_info.get("username", "").strip()
    language_code = user_info.get("language_code", "uz").strip().lower()
    photo_url = user_info.get("photo_url", "").strip()

    if user is None:
        preferred_username = tg_username or f"tg_{telegram_user_id}"
        user = User.objects.create_user(
            username=generate_unique_username(preferred_username),
            telegram_user_id=telegram_user_id,
            telegram_verified_at=timezone.now(),
        )
        is_new_user = True
    else:
        if user.status == User.Status.BLOCKED:
            raise TelegramMiniAppError("auth.user_blocked")
        if user.status == User.Status.DELETED:
            raise TelegramMiniAppError("auth.user_deleted")

    profile, _ = UserProfile.objects.get_or_create(user=user)
    changed = []

    if not profile.full_name and full_name:
        profile.full_name = full_name[:150]
        changed.append("full_name")

    if not profile.avatar_url and photo_url:
        profile.avatar_url = photo_url[:500]
        changed.append("avatar_url")

    if profile.telegram_chat_id != str(telegram_user_id):
        profile.telegram_chat_id = str(telegram_user_id)
        changed.append("telegram_chat_id")

    if not profile.telegram_notifications_enabled:
        profile.telegram_notifications_enabled = True
        changed.append("telegram_notifications_enabled")

    if language_code in {"uz", "ru", "en"} and profile.preferred_language != language_code:
        profile.preferred_language = language_code
        changed.append("preferred_language")

    if changed:
        changed.append("updated_at")
        profile.save(update_fields=changed)

    tokens = create_auth_tokens(user, device_name=device_name, ip_address=ip_address)

    return {
        "user": user,
        "tokens": tokens,
        "is_new_user": is_new_user,
    }


@transaction.atomic
def save_telegram_contact(user, phone_number):
    """
    Foydalanuvchining Telegram orqali yuborgan telefon raqamini saqlash.
    """
    from apps.accounts.managers import normalize_phone
    from apps.accounts.validators import phone_validator

    cleaned_phone = normalize_phone(phone_number)
    if not cleaned_phone:
        raise TelegramMiniAppError("auth.phone_required", "Telefon raqam kiritilmadi.")

    try:
        phone_validator(cleaned_phone)
    except Exception as error:
        raise TelegramMiniAppError("auth.invalid_phone_format", "Telefon raqam formati noto‘g‘ri.") from error

    # Agar boshqa userda bu raqam bo'lsa
    existing = User.objects.filter(phone=cleaned_phone).exclude(pk=user.pk).first()
    if existing:
        raise TelegramMiniAppError("auth.phone_already_registered", "Bu telefon raqam boshqa foydalanuvchiga biriktirilgan.")

    user.phone = cleaned_phone
    if not user.telegram_verified_at:
        user.telegram_verified_at = timezone.now()
    user.save(update_fields=["phone", "telegram_verified_at", "updated_at"])
    return user

