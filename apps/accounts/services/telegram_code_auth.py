import hashlib
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.accounts.models import User, UserProfile, TelegramLoginChallenge
from apps.accounts.services.auth_tokens import create_auth_tokens
from apps.accounts.services.telegram_web_login import get_effective_bot_username
from apps.accounts.utils import generate_unique_username

CODE_TTL_SECONDS = 60
SESSION_TTL_SECONDS = 600
MAX_CODE_ATTEMPTS = 5


class TelegramCodeAuthError(Exception):
    def __init__(self, code, detail=""):
        self.code = str(code)
        self.detail = str(detail)
        super().__init__(self.code)


def session_hash(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def code_hash(challenge, code):
    return salted_hmac("telegram-login-code", f"{challenge.pk}:{code}", algorithm="sha256").hexdigest()


def init_telegram_code_session():
    session_id = secrets.token_urlsafe(32)
    from apps.accounts.services.telegram_miniapp import get_bot_token, TelegramMiniAppError
    from apps.accounts.services.telegram_web_login import TelegramWebLoginError
    try:
        get_bot_token()
        bot_username = get_effective_bot_username(strict=True)
    except (TelegramMiniAppError, TelegramWebLoginError) as error:
        raise TelegramCodeAuthError("auth.telegram_not_configured", "Telegram bot sozlanmagan.") from error
    TelegramLoginChallenge.objects.create(session_hash=session_hash(session_id), expires_at=timezone.now() + timedelta(seconds=SESSION_TTL_SECONDS))
    return {"session_id": session_id, "bot_username": bot_username, "bot_url": f"https://t.me/{bot_username}?start=auth_{session_id}", "expires_in": CODE_TTL_SECONDS}


@transaction.atomic
def generate_telegram_code_for_user(user_info, session_id=None):
    if not session_id or not user_info.get("id"):
        raise TelegramCodeAuthError("auth.code_expired_or_invalid")
    challenge = TelegramLoginChallenge.objects.select_for_update().filter(session_hash=session_hash(session_id), used_at__isnull=True, expires_at__gt=timezone.now()).first()
    if challenge is None:
        raise TelegramCodeAuthError("auth.code_expired_or_invalid")
    if challenge.user_info and challenge.user_info.get("id") != user_info["id"]:
        raise TelegramCodeAuthError("auth.code_expired_or_invalid")
    code = str(secrets.randbelow(90000) + 10000)
    challenge.code_hash = code_hash(challenge, code)
    challenge.user_info = {key: user_info[key] for key in ("id", "first_name", "last_name", "username", "language_code") if key in user_info}
    challenge.expires_at = timezone.now() + timedelta(seconds=CODE_TTL_SECONDS)
    challenge.attempts = 0
    challenge.save(update_fields=("code_hash", "user_info", "expires_at", "attempts"))
    return code


def verify_telegram_code(code, session_id=None, device_name="Telegram Web Browser", ip_address=None):
    if not code:
        raise TelegramCodeAuthError("auth.code_required")
    cleaned_code = str(code).strip()
    if len(cleaned_code) != 5 or not cleaned_code.isascii() or not cleaned_code.isdigit():
        raise TelegramCodeAuthError("auth.invalid_code_format")
    # Commit failed attempts and consumption before issuing tokens. A transaction
    # rollback on an invalid code must not reset the attempt limit.
    payload = None
    with transaction.atomic():
        challenge = TelegramLoginChallenge.objects.select_for_update().filter(session_hash=session_hash(session_id or "")).first()
        if challenge and challenge.used_at is None and challenge.expires_at > timezone.now() and challenge.attempts < MAX_CODE_ATTEMPTS and challenge.code_hash:
            challenge.attempts += 1
            if secrets.compare_digest(challenge.code_hash, code_hash(challenge, cleaned_code)):
                payload = {"user_info": challenge.user_info}
                challenge.used_at = timezone.now()
            challenge.save(update_fields=("attempts", "used_at"))
    if payload is None:
        raise TelegramCodeAuthError("auth.code_expired_or_invalid")
    return _complete_login(payload, device_name, ip_address)


@transaction.atomic
def _complete_login(payload, device_name, ip_address):
    user_info = payload.get("user_info", {})
    telegram_user_id = user_info.get("id")
    if not telegram_user_id:
        raise TelegramCodeAuthError("auth.invalid_user_data", "Telegram foydalanuvchi ma’lumotlari topilmadi.")

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
            raise TelegramCodeAuthError("auth.user_blocked", "Foydalanuvchi hisobi bloklangan.")

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

    return {
        "user": user,
        "tokens": tokens,
        "is_new_user": is_new_user,
    }
