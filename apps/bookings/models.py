import secrets
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


def generate_booking_number():
    return str(secrets.randbelow(900_000_000_000) + 100_000_000_000)


class ReservationBase(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    zone = models.ForeignKey("clubs.Zone", on_delete=models.PROTECT, null=True, blank=True)
    barber = models.ForeignKey(
        "barbers.Barber",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="%(class)ss",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_price_tiyin = models.PositiveBigIntegerField(default=0)
    total_price_tiyin = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "bookings.end_time_before_start_time"}, code="bookings.end_time_before_start_time")
        if not self.zone_id and not self.barber_id:
            raise ValidationError("Zone yoki Barber tanlanishi shart.")
        if (
            self.zone_id
            and self.quantity is not None
            and self.quantity > self.zone.booking_capacity
        ):
            raise ValidationError({"quantity": "bookings.quantity_exceeds_capacity"}, code="bookings.quantity_exceeds_capacity")


class BookingHold(ReservationBase):
    class Status(models.TextChoices):
        HELD = "HELD", "Held"
        CONVERTED = "CONVERTED", "Converted"
        EXPIRED = "EXPIRED", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.HELD)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "booking_holds"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")),
                name="hold_ends_after_start",
            ),
        ]
        indexes = [
            models.Index(
                fields=("zone", "starts_at", "ends_at", "status"),
                name="hold_zone_time_status_idx",
            ),
            models.Index(
                fields=("barber", "starts_at", "ends_at", "status"),
                name="hold_barber_time_status_idx",
            ),
            models.Index(
                fields=("user", "status", "expires_at"),
                name="hold_user_status_exp_idx",
            ),
        ]

    def __str__(self):
        target = self.barber or self.zone
        return f"{target} — {self.starts_at:%Y-%m-%d %H:%M}"

    @property
    def is_active(self):
        return self.status == self.Status.HELD and self.expires_at > timezone.now()

    def expire(self):
        if self.status == self.Status.HELD and self.expires_at <= timezone.now():
            self.status = self.Status.EXPIRED
            self.save(update_fields=("status", "updated_at"))
            return True
        return False


class Booking(ReservationBase):
    class Status(models.TextChoices):
        PENDING_CONFIRMATION = "PENDING_CONFIRMATION", "Pending confirmation"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CHECKED_IN = "CHECKED_IN", "Checked in"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No-show"

    TRANSITIONS = {
        Status.PENDING_CONFIRMATION: {Status.CONFIRMED, Status.CANCELLED},
        Status.CONFIRMED: {Status.CHECKED_IN, Status.CANCELLED, Status.NO_SHOW},
        Status.CHECKED_IN: {Status.COMPLETED},
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_number = models.CharField(
        max_length=12,
        unique=True,
        editable=False,
        default=generate_booking_number,
    )
    hold = models.OneToOneField(
        BookingHold,
        on_delete=models.PROTECT,
        related_name="booking",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_CONFIRMATION,
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    no_show_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "bookings"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")),
                name="booking_ends_after_start",
            ),
        ]
        indexes = [
            models.Index(
                fields=("zone", "starts_at", "ends_at", "status"),
                name="booking_zone_time_status_idx",
            ),
            models.Index(
                fields=("barber", "starts_at", "ends_at", "status"),
                name="booking_barber_time_status_idx",
            ),
            models.Index(
                fields=("user", "status", "starts_at"),
                name="booking_user_status_start_idx",
            ),
        ]

    def __str__(self):
        return f"{self.id} — {self.status}"

    def can_transition_to(self, status):
        return status in self.TRANSITIONS.get(self.status, set())

    def transition_to(self, status):
        if not self.can_transition_to(status):
            raise ValidationError({"status": "bookings.invalid_status_transition"}, code="bookings.invalid_status_transition")
        self.status = status
        timestamp_field = {
            self.Status.CONFIRMED: "confirmed_at",
            self.Status.CHECKED_IN: "checked_in_at",
            self.Status.COMPLETED: "completed_at",
            self.Status.NO_SHOW: "no_show_at",
        }.get(status)
        update_fields = ["status", "updated_at"]
        if timestamp_field:
            setattr(self, timestamp_field, timezone.now())
            update_fields.append(timestamp_field)
        self.save(update_fields=update_fields)

    def save(self, *args, **kwargs):
        if self.pk:
            original = Booking.objects.filter(pk=self.pk).values_list(
                "booking_number",
                flat=True,
            ).first()
            if original and original != self.booking_number:
                raise ValidationError({"booking_number": "bookings.number_immutable"}, code="bookings.number_immutable")
        super().save(*args, **kwargs)


class Cancellation(models.Model):
    class Source(models.TextChoices):
        USER = "USER", "User"
        TELEGRAM = "TELEGRAM", "Telegram"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name="cancellation",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.USER)
    actor_name = models.CharField(max_length=150, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "booking_cancellations"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.booking_id} — {self.source}"
