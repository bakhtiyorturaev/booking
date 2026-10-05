from django.core.validators import MinValueValidator
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


class VenueBilling(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    club = models.OneToOneField("clubs.Club", on_delete=models.PROTECT, related_name="billing")
    monthly_price_tiyin = models.PositiveBigIntegerField()
    paid_until = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=Q(monthly_price_tiyin__gt=0), name="venue_billing_positive_price",
        )]


class PlatformBillingSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    paid_mode_enabled = models.BooleanField(default=False, verbose_name="Pullik rejim yoqilgan")
    grace_days = models.PositiveSmallIntegerField(default=7, validators=[MinValueValidator(0)], verbose_name="Pullik rejimga o‘tish uchun kunlar")
    paid_mode_started_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "Platforma to‘lov rejimi"
        verbose_name_plural = "Platforma to‘lov rejimi"
        constraints = [models.CheckConstraint(condition=Q(id=1), name="platform_billing_singleton")]

    def save(self, *args, **kwargs):
        self.pk = 1
        previous = type(self).objects.filter(pk=1).first()
        if self.paid_mode_enabled and (previous is None or not previous.paid_mode_enabled):
            self.paid_mode_started_at = timezone.now()
        elif not self.paid_mode_enabled:
            self.paid_mode_started_at = None
        if kwargs.get("update_fields"):
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"paid_mode_started_at"}
        super().save(*args, **kwargs)

    def __str__(self):
        return "Pullik rejim" if self.paid_mode_enabled else "Bepul rejim"


class BarberBilling(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    barber = models.OneToOneField("barbers.Barber", on_delete=models.PROTECT, related_name="billing")
    monthly_price_tiyin = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])
    paid_until = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(monthly_price_tiyin__gt=0), name="barber_billing_positive_price")]


class ManualVenuePayment(models.Model):
    class Method(models.TextChoices):
        CASH = "CASH", "Naqd"
        CARD = "CARD", "Karta"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    billing = models.ForeignKey(VenueBilling, on_delete=models.PROTECT, related_name="payments", null=True, blank=True)
    barber_billing = models.ForeignKey(BarberBilling, on_delete=models.PROTECT, related_name="payments", null=True, blank=True)
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="venue_payments")
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="collected_venue_payments")
    amount_tiyin = models.PositiveBigIntegerField()
    monthly_price_tiyin = models.PositiveBigIntegerField()
    method = models.CharField(max_length=4, choices=Method.choices)
    idempotency_key = models.UUIDField(unique=True)
    period_starts_at = models.DateTimeField()
    period_ends_at = models.DateTimeField()
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.CheckConstraint(condition=(Q(billing__isnull=False, barber_billing__isnull=True) | Q(billing__isnull=True, barber_billing__isnull=False)), name="manual_payment_single_target"),
            models.CheckConstraint(condition=Q(amount_tiyin__gt=0), name="manual_venue_payment_positive_amount"),
            models.CheckConstraint(condition=Q(monthly_price_tiyin__gt=0), name="manual_venue_payment_positive_price"),
            models.CheckConstraint(condition=Q(period_ends_at__gt=F("period_starts_at")), name="manual_venue_payment_positive_period"),
            models.CheckConstraint(condition=Q(method__in=("CASH", "CARD")), name="manual_venue_payment_valid_method"),
        ]


class VenueTariffRule(models.Model):
    service_type = models.ForeignKey("clubs.ServiceType", on_delete=models.PROTECT)
    city = models.ForeignKey("clubs.City", on_delete=models.PROTECT, null=True, blank=True)
    district = models.ForeignKey("clubs.District", on_delete=models.PROTECT, null=True, blank=True)
    monthly_price_tiyin = models.PositiveBigIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "Hudud va xizmat tarifi"
        verbose_name_plural = "Hudud va xizmat tariflari"
        constraints = [
            models.UniqueConstraint(fields=("service_type", "district"), condition=models.Q(district__isnull=False), name="venue_tariff_district_unique"),
            models.UniqueConstraint(fields=("service_type", "city"), condition=models.Q(district__isnull=True, city__isnull=False), name="venue_tariff_city_unique"),
            models.UniqueConstraint(fields=("service_type",), condition=models.Q(district__isnull=True, city__isnull=True), name="venue_tariff_default_unique"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.district_id and self.city_id != self.district.city_id:
            raise ValidationError({"district": "Tuman tanlangan shaharga tegishli bo‘lishi kerak."})

    def __str__(self):
        return f"{self.service_type} — {self.district or self.city or 'Barcha hududlar'}"
