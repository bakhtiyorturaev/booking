from django.core.cache import cache

from apps.core.models import SystemMessage, normalize_language


FALLBACK_MESSAGES = {
    "uz": "Noma’lum xatolik yuz berdi.",
    "ru": "Произошла неизвестная ошибка.",
    "en": "An unknown error occurred.",
}


def get_system_message(code, language="uz"):
    code = str(code)
    language = normalize_language(language)

    cache_key = f"system-message:{code}:{language}"
    text = cache.get(cache_key)

    if text is None:
        try:
            message = SystemMessage.objects.get(
                code=code,
                is_active=True,
            )
            text = message.get_text(language)
            cache.set(cache_key, text, timeout=3600)

        except SystemMessage.DoesNotExist:
            text = FALLBACK_MESSAGES.get(language, FALLBACK_MESSAGES["uz"])

    return {
        "code": code,
        "message": text,
    }