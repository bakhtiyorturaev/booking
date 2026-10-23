import re
import secrets
from django.conf import settings
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
    remote_address = request.META.get("REMOTE_ADDR") or None
    # `X-Forwarded-For` faqat ishonchli teskari-proksi (load balancer/nginx)
    # orqali kelganda hisobga olinadi — aks holda har qanday mijoz bu
    # headerni o'zi yuborib, IP manzilini (demak, sessiya logi/geo-bloklash
    # kabi IP-ga asoslangan tekshiruvlarni) soxtalashtirishi mumkin edi.
    if remote_address not in settings.TRUSTED_PROXY_IPS:
        return remote_address
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded_for.split(",", 1)[0].strip() or remote_address