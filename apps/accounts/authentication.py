from django.core.cache import cache
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.accounts.models import UserSession

SESSION_CACHE_TTL = 60  # seconds


def get_session_cache_key(session_id, user_id):
    return f"user_session_valid:{session_id}:{user_id}"


def invalidate_session_cache(session_id, user_id):
    if session_id and user_id:
        cache.delete(get_session_cache_key(session_id, user_id))


class SessionJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        session_id = validated_token.get("session_id")

        if not session_id:
            raise AuthenticationFailed(
                "2055",
                code="2055",
            )

        cache_key = get_session_cache_key(session_id, user.pk)
        cached_valid = cache.get(cache_key)

        if cached_valid is True:
            return user
        if cached_valid is False:
            raise AuthenticationFailed(
                "2051",
                code="2051",
            )

        session_exists = UserSession.objects.filter(
            id=session_id,
            user=user,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).exists()

        if not session_exists:
            cache.set(cache_key, False, timeout=SESSION_CACHE_TTL)
            raise AuthenticationFailed(
                "2051",
                code="2051",
            )

        cache.set(cache_key, True, timeout=SESSION_CACHE_TTL)
        return user