import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.bookings.models import Booking


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name="review",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    barber = models.ForeignKey(
        "barbers.Barber",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1, message="reviews.rating_invalid"),
            MaxValueValidator(5, message="reviews.rating_invalid"),
        ]
    )
    barber_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1, message="reviews.rating_invalid"),
            MaxValueValidator(5, message="reviews.rating_invalid"),
        ],
    )
    comment = models.CharField(max_length=1000, blank=True)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reviews"
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("club", "is_visible", "created_at"),
                name="review_club_visible_idx",
            ),
            models.Index(
                fields=("barber", "is_visible", "created_at"),
                name="review_barber_visible_idx",
            ),
        ]

    def __str__(self):
        return f"{self.club} — {self.rating}"

    def clean(self):
        super().clean()
        if not self.booking_id:
            return
        if self.booking.user_id != self.user_id:
            raise ValidationError({"booking": "reviews.permission_denied"}, code="reviews.permission_denied")
        if self.booking.status != Booking.Status.COMPLETED:
            raise ValidationError({"booking": "reviews.only_completed_booking"}, code="reviews.only_completed_booking")

        if self.booking.zone_id:
            expected_club_id = self.booking.zone.branch.club_id
        elif self.booking.barber_id:
            expected_club_id = self.booking.barber.club_id
        else:
            expected_club_id = None

        if expected_club_id and self.club_id != expected_club_id:
            raise ValidationError({"club": "reviews.permission_denied"}, code="reviews.permission_denied")
