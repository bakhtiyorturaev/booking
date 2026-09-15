from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.fields import EncryptedTextField


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
        verbose_name_plural = "Developer bot settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @property
    def is_configured(self):
        return bool(self.is_enabled and self.bot_token and self.chat_id)

    def __str__(self):
        return "Developer bot settings"

