import re
import secrets
from apps.accounts.models import User


def generate_unique_username(email):
    email_prefix = email.split("@")[0].lower()

    base_username = re.sub(r"[^a-z0-9_]","_",email_prefix,)

    base_username = re.sub(r"_+", "_", base_username,).strip("_")

    if not base_username:
        base_username = "user"

    base_username = base_username[:20]

    if not User.objects.filter(
        username=base_username,
    ).exists():
        return base_username

    while True:
        suffix = secrets.randbelow(9000) + 1000
        username = f"{base_username}_{suffix}"

        if not User.objects.filter(
            username=username,
        ).exists():
            return username


def generate_phone_username(phone):
    phone_digits = "".join(
        character
        for character in phone
        if character.isdigit()
    )

    last_digits = phone_digits[-4:] or "user"
    base_username = f"user_{last_digits}"

    if not User.objects.filter(
        username=base_username,
    ).exists():
        return base_username

    while True:
        suffix = secrets.randbelow(9000) + 1000
        username = f"{base_username}_{suffix}"

        if not User.objects.filter(
            username=username,
        ).exists():
            return username


def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")