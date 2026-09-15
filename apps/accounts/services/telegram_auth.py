import jwt
import requests

from django.db import transaction
from django.utils import timezone

from apps.accounts.managers import normalize_phone
from apps.accounts.models import User, UserProfile
from apps.accounts.services.auth_tokens import create_auth_tokens
from apps.accounts.utils import generate_unique_username
from telegram_bot.models import TelegramBotSettings


TELEGRAM_ISSUER = "https://oauth.telegram.org"
TELEGRAM_TOKEN_URL = f"{TELEGRAM_ISSUER}/token"
TELEGRAM_JWKS_URL = f"{TELEGRAM_ISSUER}/.well-known/jwks.json"


class TelegramAuthError(Exception):
    def __init__(self, code, detail=""):
        self.code = str(code)
        self.detail = str(detail)
        super().__init__(self.code)


def get_login_settings():
    configuration = TelegramBotSettings.objects.filter(pk=1).first()
    if not configuration or not configuration.is_login_configured:
        raise TelegramAuthError("auth.telegram_not_configured")
    return configuration


def exchange_telegram_code(code, code_verifier, redirect_uri):
    configuration = get_login_settings()
    try:
        response = requests.post(
            TELEGRAM_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": str(configuration.login_client_id),
                "code_verifier": code_verifier,
            },
            auth=(str(configuration.login_client_id), configuration.login_client_secret),
            timeout=configuration.request_timeout_seconds,
        )
        response.raise_for_status()
        id_token = response.json()["id_token"]
        signing_key = jwt.PyJWKClient(TELEGRAM_JWKS_URL).get_signing_key_from_jwt(id_token)
        return jwt.decode(
            id_token,
            signing_key.key,
            algorithms=("RS256", "ES256"),
            audience=str(configuration.login_client_id),
            issuer=TELEGRAM_ISSUER,
        )
    except (requests.RequestException, KeyError, ValueError, jwt.PyJWTError) as error:
        raise TelegramAuthError("auth.telegram_data_invalid", str(error)) from error


@transaction.atomic
def login_with_telegram(code, code_verifier, redirect_uri, device_name="", ip_address=None):
    claims = exchange_telegram_code(code, code_verifier, redirect_uri)
    telegram_user_id = claims.get("id") or claims.get("sub")
    phone = normalize_phone(claims.get("phone_number"))
    if not telegram_user_id or not phone or claims.get("phone_number_verified") is not True:
        raise TelegramAuthError("auth.telegram_phone_permission_required")

    user = User.objects.select_for_update().filter(
        telegram_user_id=telegram_user_id
    ).first()
    is_new_user = False
    if user is None:
        user = User.objects.select_for_update().filter(phone=phone).first()
        if user is None:
            preferred_username = claims.get("preferred_username") or f"tg_{telegram_user_id}"
            user = User.objects.create_user(
                username=generate_unique_username(preferred_username),
                phone=phone,
            )
            is_new_user = True
        user.telegram_user_id = telegram_user_id

    phone_owner = User.objects.select_for_update().filter(phone=phone).exclude(pk=user.pk).first()
    if phone_owner is not None:
        raise TelegramAuthError("auth.telegram_phone_already_linked")

    if user.status == User.Status.BLOCKED:
        raise TelegramAuthError("auth.user_blocked")
    if user.status == User.Status.DELETED:
        raise TelegramAuthError("auth.user_deleted")

    user.phone = phone
    user.phone_verified_at = timezone.now()
    user.telegram_verified_at = timezone.now()
    user.save(update_fields=(
        "phone", "phone_verified_at", "telegram_user_id",
        "telegram_verified_at", "updated_at",
    ))
    profile, _ = UserProfile.objects.get_or_create(user=user)
    changed = []
    if not profile.full_name and claims.get("name"):
        profile.full_name = claims["name"][:150]
        changed.append("full_name")
    if not profile.avatar_url and claims.get("picture"):
        profile.avatar_url = claims["picture"][:500]
        changed.append("avatar_url")
    profile.telegram_chat_id = str(telegram_user_id)
    profile.telegram_notifications_enabled = True
    changed.extend(("telegram_chat_id", "telegram_notifications_enabled", "updated_at"))
    profile.save(update_fields=changed)

    return {
        "user": user,
        "tokens": create_auth_tokens(user, device_name, ip_address),
        "is_new_user": is_new_user,
    }
