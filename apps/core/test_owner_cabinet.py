from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserProfile
from apps.accounts.serializers import AuthUserSerializer, UserSerializer
from apps.barbers.models import Barber
from apps.bookings.models import Booking, BookingHold
from apps.clubs.models import Branch, City, Club, District, Zone
from apps.reviews.models import Review


class OwnerCabinetApiTestCase(TestCase):
    """Egalar kabineti (/cabinet) — owner-scoping va ruxsatlar."""

    def setUp(self):
        self.client = APIClient()

        # Platforma admini (boshqa klub egasi)
        self.admin_user = User.objects.create_user(
            username="platform_admin",
            phone="+998901112233",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        UserProfile.objects.create(user=self.admin_user, full_name="Platforma Admin")

        # Muassasa egasi — oddiy CUSTOMER roli, lekin klub egasi (Club.owner)
        self.owner_user = User.objects.create_user(
            username="club_owner",
            phone="+998904445566",
            role=User.Role.CUSTOMER,
        )
        UserProfile.objects.create(user=self.owner_user, full_name="Klub Egasi")

        # Hech narsaga ega bo'lmagan oddiy mijoz
        self.customer_user = User.objects.create_user(
            username="plain_customer",
            phone="+998905556677",
            role=User.Role.CUSTOMER,
        )
        UserProfile.objects.create(user=self.customer_user, full_name="Oddiy Mijoz")

        self.city = City.objects.create(name="Toshkent", is_active=True)
        self.district = District.objects.create(city=self.city, name="Chilonzor", is_active=True)

        # Egaga tegishli klub
        self.owner_club = Club.objects.create(
            owner=self.owner_user,
            name="Egasi Gaming",
            slug="egasi-gaming",
            status=Club.Status.ACTIVE,
        )
        self.owner_branch = Branch.objects.create(
            club=self.owner_club,
            city=self.city,
            district=self.district,
            name="Egasi Filiali",
            address="Chilonzor 1",
            latitude=41.2858,
            longitude=69.2035,
            status=Branch.Status.ACTIVE,
        )
        self.owner_zone = Zone.objects.create(
            branch=self.owner_branch,
            name="Egasi VIP",
            resource_type=Zone.ResourceType.COMPUTER,
            capacity=10,
            unit_count=10,
            price_per_hour_tiyin=3000000,
            status=Zone.Status.ACTIVE,
        )

        # Boshqa (adminga tegishli) klub — ega ko'rmasligi kerak
        self.other_club = Club.objects.create(
            owner=self.admin_user,
            name="Admin Gaming",
            slug="admin-gaming",
            status=Club.Status.ACTIVE,
        )
        self.other_branch = Branch.objects.create(
            club=self.other_club,
            city=self.city,
            district=self.district,
            name="Admin Filiali",
            address="Yunusobod 5",
            latitude=41.36,
            longitude=69.28,
            status=Branch.Status.ACTIVE,
        )
        self.other_zone = Zone.objects.create(
            branch=self.other_branch,
            name="Admin VIP",
            resource_type=Zone.ResourceType.COMPUTER,
            capacity=10,
            unit_count=10,
            price_per_hour_tiyin=3000000,
            status=Zone.Status.ACTIVE,
        )

    def _make_completed_booking(self, zone, user, price=6000000):
        now = timezone.now()
        hold = BookingHold.objects.create(
            user=user,
            zone=zone,
            starts_at=now,
            ends_at=now + timezone.timedelta(hours=2),
            quantity=1,
            unit_price_tiyin=price // 2,
            total_price_tiyin=price,
            expires_at=now + timezone.timedelta(minutes=10),
            status=BookingHold.Status.CONVERTED,
        )
        return Booking.objects.create(
            hold=hold,
            user=user,
            zone=zone,
            starts_at=hold.starts_at,
            ends_at=hold.ends_at,
            quantity=1,
            unit_price_tiyin=price // 2,
            total_price_tiyin=price,
            status=Booking.Status.COMPLETED,
        )

    # ---- owner-stats ----

    def test_owner_stats_requires_owner_or_admin(self):
        # Anonim
        res = self.client.get("/api/v1/cabinet/owner-stats/")
        self.assertEqual(res.status_code, 401)

        # Hech narsaga ega bo'lmagan mijoz — 403
        self.client.force_authenticate(user=self.customer_user)
        res = self.client.get("/api/v1/cabinet/owner-stats/")
        self.assertEqual(res.status_code, 403)

    def test_owner_stats_scoped_to_own_clubs(self):
        self._make_completed_booking(self.owner_zone, self.customer_user, price=6000000)

        self.client.force_authenticate(user=self.owner_user)
        res = self.client.get("/api/v1/cabinet/owner-stats/")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Faqat egaga tegishli 1 ta klub ko'rinadi (adminniki emas)
        self.assertEqual(data["clubs"]["total"], 1)
        self.assertEqual(data["branches"]["total"], 1)
        self.assertIn("reviews", data)
        self.assertIn("revenue", data)
        # Tushum yakunlangan bronlardan hisoblanadi
        self.assertEqual(data["revenue"]["total_tiyin"], 6000000)

    # ---- reviews scoping ----

    def test_owner_reviews_scoped_to_own_clubs(self):
        own_booking = self._make_completed_booking(self.owner_zone, self.customer_user)
        own_review = Review.objects.create(
            booking=own_booking,
            user=self.customer_user,
            club=self.owner_club,
            rating=5,
            comment="Egasi klubi zo'r!",
            is_visible=True,
        )
        # Boshqa klubga sharh (o'zining broni bilan)
        other_booking = self._make_completed_booking(self.other_zone, self.customer_user)
        Review.objects.create(
            booking=other_booking,
            user=self.customer_user,
            club=self.other_club,
            rating=2,
            comment="Admin klubi",
            is_visible=True,
        )

        self.client.force_authenticate(user=self.owner_user)
        res = self.client.get("/api/v1/cabinet/reviews/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 1)

        # O'z sharhini boshqara oladi
        res = self.client.post(f"/api/v1/cabinet/reviews/{own_review.id}/toggle-visibility/")
        self.assertEqual(res.status_code, 200)
        own_review.refresh_from_db()
        self.assertFalse(own_review.is_visible)

    def test_owner_cannot_touch_other_club_review(self):
        other_booking = self._make_completed_booking(self.other_zone, self.customer_user)
        other_review = Review.objects.create(
            booking=other_booking,
            user=self.customer_user,
            club=self.other_club,
            rating=1,
            comment="Boshqa klub",
            is_visible=True,
        )
        self.client.force_authenticate(user=self.owner_user)
        res = self.client.post(f"/api/v1/cabinet/reviews/{other_review.id}/toggle-visibility/")
        self.assertEqual(res.status_code, 404)

    # ---- barbers scoping ----

    def test_owner_barbers_scoped_to_own_clubs(self):
        barber_user_a = User.objects.create_user(username="barber_a", phone="+998911112200")
        barber_user_b = User.objects.create_user(username="barber_b", phone="+998911112201")
        Barber.objects.create(
            user=barber_user_a,
            club=self.owner_club,
            branch=self.owner_branch,
            full_name="Egasi Sartaroshi",
        )
        Barber.objects.create(
            user=barber_user_b,
            club=self.other_club,
            branch=self.other_branch,
            full_name="Admin Sartaroshi",
        )

        self.client.force_authenticate(user=self.owner_user)
        res = self.client.get("/api/v1/cabinet/barbers/")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        results = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["full_name"], "Egasi Sartaroshi")

    # ---- clubs scoping (mavjud endpoint, egaga tekshirish) ----

    def test_owner_sees_only_own_clubs(self):
        self.client.force_authenticate(user=self.owner_user)
        res = self.client.get("/api/v1/cabinet/clubs/")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        results = payload["results"] if isinstance(payload, dict) and "results" in payload else payload
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Egasi Gaming")

    # ---- is_club_owner flag ----

    def test_auth_serializer_exposes_is_club_owner(self):
        self.assertTrue(AuthUserSerializer(self.owner_user).data["is_club_owner"])
        self.assertFalse(AuthUserSerializer(self.customer_user).data["is_club_owner"])

    def test_session_serializer_exposes_is_club_owner(self):
        # /auth/me/ (UserSerializer) — sahifa yuklanganda middleware shunga tayanadi.
        self.assertTrue(UserSerializer(self.owner_user).data["is_club_owner"])
        self.assertFalse(UserSerializer(self.customer_user).data["is_club_owner"])
