from django.core.cache import cache
from django.db import models

SUPPORTED_LANGUAGES = ("uz", "ru", "en")

def normalize_language(language):
    if not language:
        return "uz"
    raw = str(language).strip().lower()
    # Handle "uz,ru;q=0.9", "uz-UZ", "uz, uz" etc.
    first_part = raw.split(",")[0].split(";")[0].split("-")[0].strip()
    if first_part in SUPPORTED_LANGUAGES:
        return first_part
    return "uz"


class AppTranslation(models.Model):
    """
    Frontend interfeysi uchun tarjimalar.

    Misollar:
    auth.login       — Kirish
    auth.register    — Ro‘yxatdan o‘tish
    booking.create   — Bron qilish
    """
    code = models.CharField(max_length=100, unique=True)
    text_uz = models.TextField()
    text_ru = models.TextField()
    text_en = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = "app_translations"
        verbose_name = "Ilova tarjimasi"
        verbose_name_plural = "Ilova tarjimalari"

    def get_text(self, language="uz"):
        language = normalize_language(language)

        values = {
            "uz": self.text_uz,
            "ru": self.text_ru,
            "en": self.text_en,
        }

        return values.get(language) or self.text_uz or ""


    def __str__(self):
        return f"{self.code} — {self.text_uz}"

    def save(self, *args, **kwargs):
        self.full_clean()
        result = super().save(*args, **kwargs)

        for language in SUPPORTED_LANGUAGES:
            cache.delete(f"app-translations:{language}")

        return result

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)

        for language in SUPPORTED_LANGUAGES:
            cache.delete(f"app-translations:{language}")

        return result


class SystemMessage(models.Model):
    """
    Backend xatolik va muvaffaqiyat xabarlari.

    Misollar:
    auth.invalid_phone_format — Telefon formati noto‘g‘ri
    auth.otp_expired          — OTP kod eskirgan
    bookings.not_found        — Bron topilmadi
    """

    code = models.CharField(max_length=100, unique=True)
    text_uz = models.TextField()
    text_ru = models.TextField()
    text_en = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_messages"
        verbose_name = "Tizim xabari"
        verbose_name_plural = "Tizim xabarlari"

    def __str__(self):
        return f"{self.code} — {self.text_uz}"


    def get_text(self, language="uz"):
        language = normalize_language(language)

        values = {
            "uz": self.text_uz,
            "ru": self.text_ru,
            "en": self.text_en,
        }

        return values.get(language) or self.text_uz or ""

    def save(self, *args, **kwargs):
        self.full_clean()
        result = super().save(*args, **kwargs)

        for language in SUPPORTED_LANGUAGES:
            cache.delete(f"system-message:{self.code}:{language}")

        return result

    def delete(self, *args, **kwargs):
        code = self.code
        result = super().delete(*args, **kwargs)

        for language in SUPPORTED_LANGUAGES:
            cache.delete(f"system-message:{code}:{language}")

        return result