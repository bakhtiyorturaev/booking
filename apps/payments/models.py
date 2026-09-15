import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


def subscription_expires_at():
    return timezone.now() + timedelta(days=30)


class SubscriptionPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    price_tiyin = models.PositiveBigIntegerField()
    duration_days = models.PositiveSmallIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscription_plans"
        ordering = ("price_tiyin", "duration_days")
        constraints = [
            models.CheckConstraint(
                condition=Q(price_tiyin__gt=0),
                name="subscription_plan_positive_price",
            ),
            models.CheckConstraint(
                condition=Q(duration_days__gt=0),
                name="subscription_plan_positive_duration",
            ),
        ]

    def __str__(self):
        return f"{self.name} — {self.price_tiyin} tiyin"


class UserSubscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=subscription_expires_at)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_subscriptions"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("starts_at")),
                name="subscription_expires_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.status}"

    def clean(self):
        super().clean()
        if self.expires_at <= self.starts_at:
            raise ValidationError({"expires_at": "payments.expiry_before_start"}, code="payments.expiry_before_start")

    @property
    def is_active(self):
        now = timezone.now()
        return (
            self.status == self.Status.ACTIVE
            and self.starts_at <= now < self.expires_at
        )

    def activate(self):
        self.activate_for_days(30)

    def activate_for_days(self, duration_days):
        now = timezone.now()
        base_time = self.expires_at if self.is_active else now
        self.status = self.Status.ACTIVE
        self.starts_at = now
        self.expires_at = base_time + timedelta(days=duration_days)
        self.save(
            update_fields=("status", "starts_at", "expires_at", "updated_at")
        )


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    provider = models.CharField(max_length=30)
    external_id = models.CharField(max_length=150, blank=True, db_index=True)
    idempotency_key = models.CharField(max_length=100, unique=True)
    amount_tiyin = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3, default="UZS")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    checkout_url = models.URLField(max_length=1000, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "status"), name="payment_user_status_idx"),
            models.Index(fields=("provider", "external_id"), name="payment_external_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_tiyin__gt=0),
                name="payment_positive_amount",
            ),
        ]

    def __str__(self):
        return f"{self.id} — {self.status}"
