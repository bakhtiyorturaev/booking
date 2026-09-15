from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bookings.models import Booking, BookingHold
from apps.clubs.models import Branch, City, Club, Zone
from apps.reviews.models import Review
from apps.payments.models import UserSubscription


class ReviewAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="review_user",
            phone="+998901234568",
        )
        cls.subscription = UserSubscription.objects.create(user=cls.user)
        cls.club = Club.objects.create(
            owner=cls.user,
            name="Review Club",
            status=Club.Status.ACTIVE,
        )
        city = City.objects.create(name="Review City", slug="review-city")
        branch = Branch.objects.create(
            club=cls.club,
            city=city,
            name="Main",
            address="Test address",
            latitude=41,
            longitude=69,
            status=Branch.Status.ACTIVE,
        )
        zone = Zone.objects.create(
            branch=branch,
            name="Standard",
            capacity=5,
            price_per_hour_tiyin=2_000_000,
        )
        starts_at = timezone.now() - timedelta(hours=2)
        hold = BookingHold.objects.create(
            user=cls.user,
            zone=zone,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            unit_price_tiyin=2_000_000,
            total_price_tiyin=2_000_000,
            expires_at=timezone.now() - timedelta(hours=1),
            status=BookingHold.Status.CONVERTED,
        )
        cls.booking = Booking.objects.create(
            hold=hold,
            user=cls.user,
            zone=zone,
            starts_at=hold.starts_at,
            ends_at=hold.ends_at,
            quantity=1,
            unit_price_tiyin=hold.unit_price_tiyin,
            total_price_tiyin=hold.total_price_tiyin,
            status=Booking.Status.COMPLETED,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_completed_booking_can_be_reviewed(self):
        response = self.client.post(
            "/api/v1/reviews/",
            {
                "booking_id": self.booking.id,
                "rating": 5,
                "comment": "A’lo klub",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.club.refresh_from_db()
        self.assertEqual(self.club.rating, 5)
        self.assertEqual(self.club.review_count, 1)

    def test_booking_can_only_be_reviewed_once(self):
        Review.objects.create(
            booking=self.booking,
            user=self.user,
            club=self.club,
            rating=5,
        )

        response = self.client.post(
            "/api/v1/reviews/",
            {"booking_id": self.booking.id, "rating": 4},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "reviews.already_submitted")

    def test_uncompleted_booking_cannot_be_reviewed(self):
        self.booking.status = Booking.Status.CONFIRMED
        self.booking.save(update_fields=("status", "updated_at"))

        response = self.client.post(
            "/api/v1/reviews/",
            {"booking_id": self.booking.id, "rating": 4},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "reviews.only_completed_booking")

    def test_free_user_cannot_write_review(self):
        self.subscription.delete()

        response = self.client.post(
            "/api/v1/reviews/",
            {"booking_id": self.booking.id, "rating": 5},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "payments.active_paid_subscription_required")

    def test_public_club_reviews_are_available(self):
        Review.objects.create(
            booking=self.booking,
            user=self.user,
            club=self.club,
            rating=5,
            comment="Yaxshi",
        )

        response = APIClient().get(f"/api/v1/clubs/{self.club.id}/reviews/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_deleting_review_recalculates_club_rating(self):
        review = Review.objects.create(
            booking=self.booking,
            user=self.user,
            club=self.club,
            rating=5,
        )
        self.club.rating = 5
        self.club.review_count = 1
        self.club.save(update_fields=("rating", "review_count"))

        response = self.client.delete(f"/api/v1/reviews/{review.id}/")

        self.assertEqual(response.status_code, 204)
        self.club.refresh_from_db()
        self.assertEqual(self.club.rating, 0)
        self.assertEqual(self.club.review_count, 0)
