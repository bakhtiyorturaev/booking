from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count

from apps.bookings.models import Booking
from apps.clubs.models import Club
from apps.reviews.models import Review
from apps.payments.services import require_paid_access


def refresh_club_rating(club_id):
    if not club_id:
        return
    values = Review.objects.filter(
        club_id=club_id,
        is_visible=True,
    ).aggregate(rating=Avg("rating"), count=Count("id"))
    rating = Decimal(str(values["rating"] or 0)).quantize(Decimal("0.01"))
    Club.objects.filter(pk=club_id).update(
        rating=rating,
        review_count=values["count"],
    )


def refresh_barber_rating(barber_id):
    if not barber_id:
        return
    from apps.barbers.models import Barber
    values = Review.objects.filter(
        barber_id=barber_id,
        is_visible=True,
    ).aggregate(rating=Avg("barber_rating"), count=Count("id"))
    if values["rating"] is None:
        values = Review.objects.filter(
            barber_id=barber_id,
            is_visible=True,
        ).aggregate(rating=Avg("rating"), count=Count("id"))
    rating = Decimal(str(values["rating"] or 0)).quantize(Decimal("0.01"))
    Barber.objects.filter(pk=barber_id).update(
        rating=rating,
        review_count=values["count"],
    )


@transaction.atomic
def create_review(user, booking_id, rating, comment="", barber_rating=None):
    require_paid_access(user)
    booking = Booking.objects.select_for_update().select_related(
        "zone__branch__club", "barber__club"
    ).get(pk=booking_id)
    if booking.user_id != user.id:
        raise ValidationError("reviews.permission_denied", code="reviews.permission_denied")
    if booking.status != Booking.Status.COMPLETED:
        raise ValidationError("reviews.only_completed_booking", code="reviews.only_completed_booking")
    if Review.objects.filter(booking=booking).exists():
        raise ValidationError("reviews.already_submitted", code="reviews.already_submitted")

    club = booking.zone.branch.club if booking.zone else (booking.barber.club if booking.barber else None)
    if not club:
        raise ValidationError("reviews.permission_denied", code="reviews.permission_denied")

    review = Review(
        booking=booking,
        user=user,
        club=club,
        barber=booking.barber,
        rating=rating,
        barber_rating=barber_rating or rating,
        comment=comment,
    )
    review.full_clean()
    review.save()
    refresh_club_rating(review.club_id)
    if review.barber_id:
        refresh_barber_rating(review.barber_id)
    return review


@transaction.atomic
def update_review(user, review, rating=None, comment=None, barber_rating=None):
    require_paid_access(user)
    update_fields = ["updated_at"]
    if rating is not None:
        review.rating = rating
        update_fields.append("rating")
    if barber_rating is not None:
        review.barber_rating = barber_rating
        update_fields.append("barber_rating")
    if comment is not None:
        review.comment = comment
        update_fields.append("comment")
    review.full_clean()
    review.save(update_fields=update_fields)
    refresh_club_rating(review.club_id)
    if review.barber_id:
        refresh_barber_rating(review.barber_id)
    return review


@transaction.atomic
def delete_review(review):
    club_id = review.club_id
    barber_id = review.barber_id
    review.delete()
    refresh_club_rating(club_id)
    if barber_id:
        refresh_barber_rating(barber_id)
