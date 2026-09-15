import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.fields import EncryptedTextField
from apps.core.models import normalize_language


class TelegramGroup(models.Model):
    class Language(models.TextChoices):
        UZ = "uz", "O‘zbek"
        RU = "ru", "Русский"
        EN = "en", "English"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    chat_id = models.BigIntegerField(unique=True)
    language = models.CharField(
        max_length=2,
        choices=Language.choices,
        default=Language.UZ,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "telegram_groups"
        ordering = ("name",)

    def __str__(self):
        return self.name


class BranchTelegramBinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.OneToOneField(
        "clubs.Branch",
        on_delete=models.CASCADE,
        related_name="telegram_binding",
    )
    group = models.ForeignKey(
        TelegramGroup,
        on_delete=models.PROTECT,
        related_name="branch_bindings",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "branch_telegram_bindings"

    def __str__(self):
        return f"{self.branch} → {self.group}"


class TelegramMessageTemplate(models.Model):
    class Event(models.TextChoices):
        PENDING = "PENDING", "Pending booking"
        CONFIRMED = "CONFIRMED", "Confirmed booking"
        CANCELLED = "CANCELLED", "Cancelled booking"

    event = models.CharField(max_length=20, choices=Event.choices, unique=True)
    text_uz = models.TextField()
    text_ru = models.TextField()
    text_en = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "telegram_message_templates"

    def __str__(self):
        return self.get_event_display()

    def get_text(self, language="uz"):
        return getattr(self, f"text_{normalize_language(language)}")


class TelegramBotSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    is_enabled = models.BooleanField(default=False)
    bot_token = EncryptedTextField(blank=True)
    login_client_id = models.BigIntegerField(null=True, blank=True)
    login_client_secret = EncryptedTextField(blank=True)
    test_group_chat_id = models.BigIntegerField(null=True, blank=True)
    request_timeout_seconds = models.PositiveSmallIntegerField(
        default=20,
        validators=(MinValueValidator(1), MaxValueValidator(60)),
    )
    polling_timeout_seconds = models.PositiveSmallIntegerField(
        default=25,
        validators=(MinValueValidator(1), MaxValueValidator(60)),
    )
    retry_delay_seconds = models.PositiveSmallIntegerField(
        default=2,
        validators=(MinValueValidator(1), MaxValueValidator(300)),
    )
    auto_confirm_enabled = models.BooleanField(default=True)
    confirmation_timeout_minutes = models.PositiveSmallIntegerField(
        default=5,
        validators=(MinValueValidator(1), MaxValueValidator(1440)),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "telegram_bot_settings"
        verbose_name_plural = "Telegram bot settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @property
    def is_configured(self):
        return bool(self.is_enabled and self.bot_token)

    @property
    def is_login_configured(self):
        return bool(self.is_enabled and self.login_client_id and self.login_client_secret)

    def __str__(self):
        return "Telegram bot settings"


class TelegramCancellationReason(models.Model):
    code = models.SlugField(max_length=20, unique=True)
    title_uz = models.CharField(max_length=100)
    title_ru = models.CharField(max_length=100)
    title_en = models.CharField(max_length=100)
    reason_uz = models.CharField(max_length=500)
    reason_ru = models.CharField(max_length=500)
    reason_en = models.CharField(max_length=500)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "telegram_cancellation_reasons"
        ordering = ("sort_order", "code")

    def get_title(self, language="uz"):
        return getattr(self, f"title_{normalize_language(language)}")

    def get_reason(self, language="uz"):
        return getattr(self, f"reason_{normalize_language(language)}")

    def __str__(self):
        return f"{self.code} — {self.title_uz}"


class TelegramBookingMessage(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    class Operation(models.TextChoices):
        SEND = "SEND", "Send"
        EDIT = "EDIT", "Edit"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="telegram_message",
    )
    group = models.ForeignKey(TelegramGroup, on_delete=models.PROTECT)
    message_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    operation = models.CharField(
        max_length=10,
        choices=Operation.choices,
        default=Operation.SEND,
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    acted_by_telegram_id = models.BigIntegerField(null=True, blank=True)
    acted_by_name = models.CharField(max_length=150, blank=True)
    acted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "telegram_booking_messages"
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.booking.booking_number} — {self.status}"
