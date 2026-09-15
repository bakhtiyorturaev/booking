import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    action = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    status_code = models.PositiveSmallIntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    request_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("actor", "created_at"), name="audit_actor_created_idx"),
            models.Index(fields=("path", "created_at"), name="audit_path_created_idx"),
        ]

    def __str__(self):
        return f"{self.method} {self.path} — {self.status_code}"
