from urllib.parse import urlparse

from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.security, deploy=True)
def check_production_origins(app_configs, **kwargs):
    if settings.DEBUG:
        return []

    issues = []
    if "*" in settings.ALLOWED_HOSTS:
        issues.append(Warning(
            "Productionda ALLOWED_HOSTS barcha domenlarga ochiq.",
            hint="DJANGO_ALLOWED_HOSTS uchun sayt domenlari va backend kabi ichki hostlarni aniq yozing.",
            id="core.W101",
        ))
    for name in ("CSRF_TRUSTED_ORIGINS", "CORS_ALLOWED_ORIGINS"):
        if any(urlparse(origin).scheme != "https" for origin in getattr(settings, name, [])):
            issues.append(Warning(
                f"Productionda {name} ichida HTTPS bo‘lmagan manzil bor.",
                hint="Faqat foydalaniladigan HTTPS originlarni qoldiring.",
                id="core.W102",
            ))
    for name in ("FRONTEND_URL", "TELEGRAM_MINIAPP_URL"):
        url = urlparse(getattr(settings, name, ""))
        if url.scheme != "https" or not url.hostname or url.hostname in {"localhost", "127.0.0.1", "::1"}:
            issues.append(Warning(
                f"Productionda {name} haqiqiy HTTPS saytiga sozlanmagan.",
                hint="Saytning HTTPS manzilini .env orqali belgilang.",
                id="core.W103",
            ))
    return issues
