from django.core.cache import cache

from apps.core.models import AppTranslation, normalize_language

def get_app_translations(language="uz"):
    language = normalize_language(language)
    cache_key = f"app-translations:{language}"

    translations = cache.get(cache_key)

    if translations is None:
        language_field = f"text_{language}"

        translations = dict(AppTranslation.objects.filter(is_active=True,
            ).values_list(
                "code",
                language_field,
            )
        )

        cache.set(cache_key, translations, timeout=3600)

    return translations