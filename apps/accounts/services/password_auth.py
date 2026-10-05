from django.db import models
from django.utils import timezone
from apps.accounts.managers import normalize_phone
from apps.accounts.models import User
from apps.accounts.services.auth_tokens import create_auth_tokens


class PasswordAuthError(Exception):
    def __init__(self, code):
        self.code = str(code)
        super().__init__(self.code)


def login_with_password(login, password, device_name="", ip_address=None, login_type=""):
    if not login or not password:
        raise PasswordAuthError("auth.invalid_credentials")

    login = str(login).strip()
    normalized_p = normalize_phone(login)

    lookup = models.Q(username__iexact=login)
    if normalized_p:
        lookup |= models.Q(phone=normalized_p)

    user = User.objects.filter(lookup).first()

    if not user or not user.has_usable_password() or not user.check_password(password):
        raise PasswordAuthError("auth.invalid_credentials")

    if not user.is_active:
        raise PasswordAuthError("auth.user_inactive")

    is_staff = (
        user.is_staff
        or user.is_superuser
        or user.role in {User.Role.ADMIN, User.Role.MODERATOR}
    )
    is_operator = user.role == User.Role.CLIENT or user.owned_clubs.exists() or hasattr(user, "barber_profile")
    if login_type == "staff" and not is_staff:
        raise PasswordAuthError("auth.staff_access_denied")
    if login_type == "client" and not (is_operator or is_staff):
        raise PasswordAuthError("auth.client_access_denied")
    if not (is_staff or is_operator):
        raise PasswordAuthError("auth.staff_access_denied")

    tokens = create_auth_tokens(user, device_name=device_name, ip_address=ip_address)

    return {
        "user": user,
        "tokens": tokens,
        "password_expired": user.is_password_expired,
    }


def change_user_password(user, old_password, new_password, device_name="", ip_address=None):
    if not user or not user.is_authenticated:
        raise PasswordAuthError("auth.unauthorized")

    if not user.check_password(old_password):
        raise PasswordAuthError("auth.invalid_old_password")

    user.set_password(new_password)
    user.save(update_fields=["password", "password_changed_at", "updated_at"])

    tokens = create_auth_tokens(user, device_name=device_name, ip_address=ip_address)

    return {
        "user": user,
        "tokens": tokens,
        "password_expired": False,
    }
