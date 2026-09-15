from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserProfile
from apps.bookings.models import Booking, BookingHold
from apps.clubs.models import Branch, City, Club, District, Zone
from apps.payments.models import Payment, SubscriptionPlan
from apps.reviews.models import Review


class CabinetStaffApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Admin user
        self.admin_user = User.objects.create_user(
            username="head_admin",
            phone="+998901112233",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        UserProfile.objects.create(user=self.admin_user, full_name="Bosh Admin")

        # Moderator user
        self.moderator_user = User.objects.create_user(
            username="moderator_one",
            phone="+998902223344",
            role=User.Role.MODERATOR,
            is_staff=True,
        )
        UserProfile.objects.create(user=self.moderator_user, full_name="Moderator Xodim")

        # Customer user
        self.customer_user = User.objects.create_user(
            username="customer_ali",
            phone="+998903334455",
            role=User.Role.CUSTOMER,
        )
        UserProfile.objects.create(user=self.customer_user, full_name="Ali Valiyev")

        # Location & Club setup
        self.city = City.objects.create(name="Toshkent", is_active=True)
        self.district = District.objects.create(city=self.city, name="Chilonzor", is_active=True)
        self.club = Club.objects.create(
            owner=self.admin_user,
            name="Navo Gaming",
            slug="navo-gaming",
            status=Club.Status.ACTIVE,
        )
        self.branch = Branch.objects.create(
            club=self.club,
            city=self.city,
            district=self.district,
            name="Chilonzor Filiali",
            address="Chilonzor 9",
            latitude=41.2858,
            longitude=69.2035,
            status=Branch.Status.ACTIVE,
        )
        self.zone = Zone.objects.create(
            branch=self.branch,
            name="VIP Zone",
            resource_type=Zone.ResourceType.COMPUTER,
            capacity=10,
            unit_count=10,
            price_per_hour_tiyin=3000000,
            status=Zone.Status.ACTIVE,
        )

    def test_unauthorized_and_customer_denied_from_stats(self):
        # Anonymous
        res = self.client.get("/api/v1/cabinet/stats/")
        self.assertEqual(res.status_code, 401)

        # Customer
        self.client.force_authenticate(user=self.customer_user)
        res = self.client.get("/api/v1/cabinet/stats/")
        self.assertEqual(res.status_code, 403)

    def test_admin_and_moderator_can_access_stats(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get("/api/v1/cabinet/stats/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("clubs", data)
        self.assertIn("bookings", data)
        self.assertIn("users", data)
        self.assertIn("revenue", data)
        self.assertEqual(data["clubs"]["total"], 1)

    def test_cabinet_users_crud_and_actions(self):
        self.client.force_authenticate(user=self.admin_user)

        # List
        res = self.client.get("/api/v1/cabinet/users/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.json()["count"], 3)

        # Toggle status
        res = self.client.post(f"/api/v1/cabinet/users/{self.customer_user.id}/toggle-status/")
        self.assertEqual(res.status_code, 200)
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.status, User.Status.BLOCKED)

        # Set role
        res = self.client.post(
            f"/api/v1/cabinet/users/{self.customer_user.id}/set-role/",
            {"role": "MODERATOR"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.role, User.Role.MODERATOR)

    def test_cabinet_reviews_moderation(self):
        # Create a booking and review
        now = timezone.now()
        hold = BookingHold.objects.create(
            user=self.customer_user,
            zone=self.zone,
            starts_at=now,
            ends_at=now + timezone.timedelta(hours=2),
            quantity=1,
            unit_price_tiyin=3000000,
            total_price_tiyin=6000000,
            expires_at=now + timezone.timedelta(minutes=10),
            status=BookingHold.Status.CONVERTED,
        )
        booking = Booking.objects.create(
            hold=hold,
            user=self.customer_user,
            zone=self.zone,
            starts_at=hold.starts_at,
            ends_at=hold.ends_at,
            quantity=1,
            unit_price_tiyin=3000000,
            total_price_tiyin=6000000,
            status=Booking.Status.COMPLETED,
        )
        review = Review.objects.create(
            booking=booking,
            user=self.customer_user,
            club=self.club,
            rating=5,
            comment="Ajoyib club!",
            is_visible=True,
        )

        self.client.force_authenticate(user=self.moderator_user)

        # List reviews
        res = self.client.get("/api/v1/cabinet/reviews/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 1)

        # Toggle visibility
        res = self.client.post(f"/api/v1/cabinet/reviews/{review.id}/toggle-visibility/")
        self.assertEqual(res.status_code, 200)
        review.refresh_from_db()
        self.assertFalse(review.is_visible)

    def test_cabinet_payments_list_and_summary(self):
        plan = SubscriptionPlan.objects.create(
            code="monthly_pro",
            name="Pro Plan",
            price_tiyin=5000000,
            duration_days=30,
        )
        Payment.objects.create(
            user=self.customer_user,
            plan=plan,
            provider="payme",
            idempotency_key="idemp_1",
            amount_tiyin=5000000,
            status=Payment.Status.PAID,
            paid_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.admin_user)

        res = self.client.get("/api/v1/cabinet/payments/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 1)

        res = self.client.get("/api/v1/cabinet/payments/summary/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total_paid_sum_tiyin"], 5000000)
