import uuid

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils.text import slugify

from apps.core.fields import EncryptedTextField

SUPPORTED_LANGUAGES = ("uz", "ru", "en")


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ServiceType(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    name_ru = models.CharField("Ruscha nom", max_length=100, blank=True, default="")
    name_en = models.CharField("Inglizcha nom", max_length=100, blank=True, default="")
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="children", verbose_name="Asosiy xizmat",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "clubs_servicetype"
        ordering = ("sort_order", "name")
        verbose_name = "Xizmat turi"
        verbose_name_plural = "Xizmat turlari"

    def __str__(self):
        names = [self.name]
        seen = {self.pk}
        parent = self.parent if self.parent_id else None
        while parent and parent.pk not in seen:
            seen.add(parent.pk)
            names.insert(0, parent.name)
            parent = parent.parent if parent.parent_id else None
        return " → ".join(names)

    def clean(self):
        super().clean()
        seen = {self.pk}
        parent = ServiceType.objects.filter(pk=self.parent_id).first() if self.parent_id else None
        if parent:
            self.parent = parent
        while parent:
            if parent.pk in seen:
                raise ValidationError({"parent": "Xizmat o‘ziga yoki ichki xizmatiga biriktirilmaydi."})
            seen.add(parent.pk)
            parent = parent.parent if parent.parent_id else None
        previous = ServiceType.objects.filter(pk=self.pk).values("parent_id").first()
        if previous and previous["parent_id"] != self.parent_id:
            from apps.clubs.models import Branch
            from apps.core.services.service_types import descendant_service_ids
            affected = descendant_service_ids([self.pk])
            overrides = {self.pk: self.parent_id}
            branches = Branch.objects.filter(
                models.Q(enabled_services__in=affected) | models.Q(zones__service_type_id__in=affected)
            ).select_related("club").prefetch_related("enabled_services", "club__available_services", "zones").distinct()
            for branch in branches:
                enabled = {service.pk for service in branch.enabled_services.all()}
                club_services = {service.pk for service in branch.club.available_services.all()}
                allowed = descendant_service_ids(club_services, parent_overrides=overrides)
                zone_services = {zone.service_type_id for zone in branch.zones.all() if zone.service_type_id}
                if not enabled.issubset(allowed) or not zone_services.issubset(descendant_service_ids(enabled, parent_overrides=overrides)):
                    raise ValidationError({"parent": "Avval bu xizmatni tegishli klub va filiallarga alohida biriktiring."})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            list(ServiceType.objects.select_for_update().values_list("pk", flat=True))
            self.clean()
            result = super().save(*args, **kwargs)
            from apps.clubs.models import Club
            from apps.core.services.service_types import descendant_service_ids, root_service
            root = root_service(self)
            category = root.code if root.code in Club.Category.values else Club.Category.OTHER
            Club.objects.filter(service_type_id__in=descendant_service_ids([self.pk])).update(category=category)
            Club.objects.filter(service_type_id=self.pk).update(service_name=self.name)
            return result


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


class City(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, help_text="Shahar nomi.")
    slug = models.SlugField(max_length=140, unique=True, help_text="Shahar kodi.")
    is_active = models.BooleanField(default=True, help_text="Tanlash uchun faolmi.")
    sort_order = models.PositiveSmallIntegerField(default=0, help_text="Ko‘rinish tartibi.")

    class Meta:
        db_table = "cities"
        verbose_name = "Shahar"
        verbose_name_plural = "Shaharlar"
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "city"
            candidate = base
            number = 2
            while City.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f"{base}-{number}"
                number += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class District(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="districts",
        help_text="Tuman tegishli shahar.",
    )
    name = models.CharField(max_length=120, help_text="Tuman nomi.")
    slug = models.SlugField(max_length=140, help_text="Tuman kodi.")
    is_active = models.BooleanField(default=True, help_text="Tanlash uchun faolmi.")
    sort_order = models.PositiveSmallIntegerField(default=0, help_text="Ko‘rinish tartibi.")

    class Meta:
        db_table = "districts"
        verbose_name = "Tuman"
        verbose_name_plural = "Tumanlar"
        ordering = ("city__sort_order", "city__name", "sort_order", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["city", "slug"],
                name="unique_district_slug_per_city",
            ),
            models.UniqueConstraint(
                fields=["city", "name"],
                name="unique_district_name_per_city",
            ),
        ]
        indexes = [
            models.Index(
                fields=["city", "is_active", "sort_order"],
                name="district_city_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.city.name} — {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "district"
            candidate = base
            number = 2
            while (
                District.objects.exclude(pk=self.pk)
                .filter(city_id=self.city_id, slug=candidate)
                .exists()
            ):
                candidate = f"{base}-{number}"
                number += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class DeveloperBotSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    is_enabled = models.BooleanField(default=False)
    bot_token = EncryptedTextField(blank=True)
    chat_id = models.BigIntegerField(null=True, blank=True)
    environment = models.CharField(max_length=50, default="development")
    request_timeout_seconds = models.PositiveSmallIntegerField(
        default=5,
        validators=(MinValueValidator(1), MaxValueValidator(60)),
    )
    notify_errors = models.BooleanField(default=True)
    notify_user_events = models.BooleanField(default=True)
    notify_booking_events = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "developer_bot_settings"
        verbose_name = "Dasturchi boti sozlamasi"
        verbose_name_plural = "Dasturchi boti sozlamalari"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @property
    def is_configured(self):
        return bool(self.is_enabled and self.bot_token and self.chat_id)

    def __str__(self):
        return "Dasturchi boti sozlamalari"
