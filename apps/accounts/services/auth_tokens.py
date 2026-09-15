import hashlib
import uuid
import hmac

from rest_framework_simplejwt.exceptions import TokenError

from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserSession
from apps.accounts.authentication import invalidate_session_cache


class AuthTokenError(Exception):
    def __init__(self, code):
        self.code = str(code)
        super().__init__(self.code)


def hash_refresh_token(raw_token):
    return hashlib.sha256(
        raw_token.encode("utf-8")
    ).hexdigest()


def public_auth_tokens(tokens):
    return {
        "access": tokens["access"],
        "refresh": tokens["refresh"],
    }



@transaction.atomic
def create_auth_tokens(
    user,
    device_name="",
    ip_address=None,
):
    if not user.is_active:
        raise AuthTokenError("auth.user_inactive")

    session = UserSession(
        id=uuid.uuid4(),
        user=user,
        device_name=device_name or "",
        ip_address=ip_address,
        expires_at=(
            timezone.now()
            + api_settings.REFRESH_TOKEN_LIFETIME
        ),
    )

    refresh_token = RefreshToken.for_user(user)

    refresh_token["session_id"] = str(session.id)
    refresh_token["role"] = user.role

    raw_refresh_token = str(refresh_token)
    access_token = str(refresh_token.access_token)

    session.refresh_token_hash = hash_refresh_token(
        raw_refresh_token
    )
    session.save()

    user.last_login = timezone.now()
    user.save(
        update_fields=[
            "last_login",
            "updated_at",
        ]
    )

    return {
        "access": access_token,
        "refresh": raw_refresh_token,
        "session_id": str(session.id),
    }


@transaction.atomic
def refresh_auth_tokens(raw_refresh_token):
    if not raw_refresh_token:
        raise AuthTokenError("auth.refresh_token_missing")

    try:
        old_refresh = RefreshToken(raw_refresh_token)
    except TokenError as error:
        raise AuthTokenError("auth.refresh_token_missing") from error

    session_id = old_refresh.get("session_id")

    if not session_id:
        raise AuthTokenError("auth.session_id_missing")

    try:
        session = (
            UserSession.objects
            .select_for_update()
            .select_related("user")
            .get(id=session_id)
        )
    except UserSession.DoesNotExist as error:
        raise AuthTokenError("auth.session_expired") from error

    if (
        session.revoked_at is not None
        or timezone.now() >= session.expires_at
    ):
        raise AuthTokenError("auth.session_expired")

    provided_hash = hash_refresh_token(
        raw_refresh_token
    )

    if not hmac.compare_digest(
        provided_hash,
        session.refresh_token_hash,
    ):
        raise AuthTokenError("auth.session_revoked_token_reused")

    user = session.user

    if not user.is_active:
        session.revoked_at = timezone.now()

        session.save(
            update_fields=["revoked_at"]
        )
        invalidate_session_cache(session_id, user.pk)

        raise AuthTokenError("auth.user_inactive")

    return {
        "access": str(old_refresh.access_token),
        "refresh": raw_refresh_token,
        "session_id": str(session.id),
    }


@transaction.atomic
def revoke_user_session(user, session_id):
    if not session_id:
        raise AuthTokenError("auth.session_id_missing")

    try:
        session = (
            UserSession.objects
            .select_for_update()
            .get(
                id=session_id,
                user=user,
            )
        )
    except UserSession.DoesNotExist as error:
        raise AuthTokenError("auth.session_expired") from error

    if session.revoked_at is None:
        session.revoked_at = timezone.now()

        session.save(
            update_fields=["revoked_at"]
        )
        invalidate_session_cache(session_id, user.pk)

    return session
