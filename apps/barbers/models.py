import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models


MAX_IMAGE_SIZE = 5 * 1024 * 1024
IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp")
IMAGE_VALIDATORS = (
    FileExtensionValidator(
        allowed_extensions=IMAGE_EXTENSIONS,
        message="barbers.invalid_image_format",
        code="barbers.invalid_image_format",
    ),
)


def barber_photo_upload_to(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"barbers/{instance.id}/photo/{uuid.uuid4().hex}{extension}"


class Barber(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Ishda"
        BREAK = "BREAK", "Tanaffusda"
        NOT_AT_WORK = "NOT_AT_WORK", "Ishga chiqmagan"
        DAY_OFF = "DAY_OFF", "Dam olish kuni"

    class AffiliationStatus(models.TextChoices):
        NONE = "NONE", "Birikmagan"
        PENDING = "PENDING", "Tasdiq kutilmoqda"
        APPROVED = "APPROVED", "Tasdiqlangan"
        REJECTED = "REJECTED", "Rad etilgan"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="barber_profile",
        help_text="Sartarosh foydalanuvchi akkaunti.",
    )
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="barbers",
        help_text="Sartaroshxona.",
    )
    branch = models.ForeignKey(
        "clubs.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="barbers",
        help_text="Sartaroshxona filiali.",
    )
    affiliation_status = models.CharField(
        max_length=15,
        choices=AffiliationStatus.choices,
        default=AffiliationStatus.NONE,
        help_text="Sartaroshxonaga birikish holati.",
    )
    full_name = models.CharField(max_length=180, help_text="Sartaroshning to'liq ismi.")
    phone = models.CharField(max_length=20, blank=True, help_text="Aloqa telefoni.")
    photo = models.ImageField(
        upload_to=barber_photo_upload_to,
        blank=True,
        validators=IMAGE_VALIDATORS,
        help_text="Sartaroshning fotosurati.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
        help_text="Real vaqt holati (Ishda, Tanaffusda, Ishga chiqmagan, Dam olish kuni).",
    )
    work_start_time = models.TimeField(default="09:00", help_text="Ish boshlanish vaqti.")
    work_end_time = models.TimeField(default="20:00", help_text="Ish tugash vaqti.")
    working_days = models.JSONField(
        default=list,
        blank=True,
        help_text="Ish kunlari ro'yxati (1=Dushanba ... 7=Yakshanba).",
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Sartarosh reytingi.",
    )
    review_count = models.PositiveIntegerField(default=0, help_text="Sharhlar soni.")
    is_active = models.BooleanField(default=True, help_text="Faollik holati.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "barbers"
        ordering = ("-rating", "-created_at")

    def __str__(self):
        return self.full_name or f"Barber #{self.id}"

    def default_working_days(self):
        return [1, 2, 3, 4, 5, 6]

    def save(self, *args, **kwargs):
        if not self.working_days:
            self.working_days = self.default_working_days()
        super().save(*args, **kwargs)
