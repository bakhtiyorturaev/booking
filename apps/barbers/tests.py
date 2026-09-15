from datetime import date, time, timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.barbers.services import get_barber_available_slots
from apps.bookings.models import Booking
from apps.clubs.models import Branch, City, Club, District
from apps.reviews.models import Review


class BarberTests(APITestCase):
    def setUp(self):
        self.city = City.objects.create(name="Tashkent", slug="tashkent")
        self.district = District.objects.create(name="Yunusobod", slug="yunusobod", city=self.city)
        self.owner = User.objects.create_user(
            username="owner_user",
            phone="+998901111111",
            role=User.Role.ADMIN,
        )
        self.barbershop = Club.objects.create(
            name="Gentleman Barbershop",
            slug="gentleman-barbershop",
            category=Club.Category.BARBERSHOP,
            owner=self.owner,
            status=Club.Status.ACTIVE,
        )
        self.branch = Branch.objects.create(
            club=self.barbershop,
            name="Main Branch",
            city=self.city,
            district=self.district,
            address="Amir Temur 10",
            latitude="41.311081",
            longitude="69.240562",
            status=Branch.Status.ACTIVE,
        )

        self.barber_user = User.objects.create_user(
            username="barber_alisher",
            phone="+998902222222",
            role=User.Role.CUSTOMER,
        )
        self.barber = Barber.objects.create(
            user=self.barber_user,
            full_name="Master Alisher",
            phone="+998902222222",
            club=self.barbershop,
            branch=self.branch,
            affiliation_status=Barber.AffiliationStatus.APPROVED,
            status=Barber.Status.AVAILABLE,
            work_start_time=time(9, 0),
            work_end_time=time(20, 0),
            working_days=[1, 2, 3, 4, 5, 6, 7],
            is_active=True,
        )

        self.customer = User.objects.create_user(
            username="customer_john",
            phone="+998903333333",
            role=User.Role.CUSTOMER,
        )

        self.staff_admin = User.objects.create_user(
            username="staff_admin",
            phone="+998904444444",
            role=User.Role.ADMIN,
            is_staff=True,
        )

    def test_public_barbers_list(self):
        url = "/api/v1/barbers/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get("results") if isinstance(data, dict) else data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["full_name"], "Master Alisher")
        self.assertEqual(results[0]["club_name"], "Gentleman Barbershop")

    def test_barber_availability_slots(self):
        target_date = date.today() + timedelta(days=1)
        res = get_barber_available_slots(self.barber, target_date)
        slots = res["slots"]
        self.assertTrue(len(slots) > 0)
        self.assertEqual(slots[0]["hour"], 9)
        self.assertEqual(slots[0]["time_label"], "09:00 - 10:00")
        self.assertTrue(slots[0]["is_available"])

        # Test availability endpoint
        url = f"/api/v1/barbers/{self.barber.id}/availability/?date={target_date.isoformat()}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["barber_id"], str(self.barber.id))
        self.assertTrue(len(data["slots"]) > 0)

    def test_barber_status_affects_availability(self):
        target_date = date.today()
        # When barber is NOT_AT_WORK
        self.barber.status = Barber.Status.NOT_AT_WORK
        self.barber.save()
        res = get_barber_available_slots(self.barber, target_date)
        self.assertFalse(res["is_available"])
        self.assertEqual(len(res["slots"]), 0)

        # When barber is DAY_OFF
        self.barber.status = Barber.Status.DAY_OFF
        self.barber.save()
        res = get_barber_available_slots(self.barber, target_date)
        self.assertFalse(res["is_available"])
        self.assertEqual(len(res["slots"]), 0)

    def test_barber_self_service_profile_and_status(self):
        self.client.force_authenticate(user=self.barber_user)

        # Get my profile
        response = self.client.get("/api/v1/barbers/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["full_name"], "Master Alisher")

        # Change status to BREAK
        response = self.client.patch("/api/v1/barbers/me/status/", {"status": Barber.Status.BREAK})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.barber.refresh_from_db()
        self.assertEqual(self.barber.status, Barber.Status.BREAK)

    def test_barber_affiliate_request(self):
        # Create new barber user
        new_barber_user = User.objects.create_user(
            username="new_barber_user",
            phone="+998905555555",
            role=User.Role.CUSTOMER,
        )
        self.client.force_authenticate(user=new_barber_user)

        response = self.client.post("/api/v1/barbers/me/affiliate/", {
            "club_id": str(self.barbershop.id),
            "branch_id": str(self.branch.id),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_barber = Barber.objects.get(user=new_barber_user)
        self.assertEqual(new_barber.affiliation_status, Barber.AffiliationStatus.PENDING)
        self.assertEqual(new_barber.club, self.barbershop)

    def test_customer_book_barber(self):
        from apps.barbers.services import TASHKENT_TZ

        self.client.force_authenticate(user=self.customer)
        now_local = timezone.localtime(timezone.now(), TASHKENT_TZ)
        starts_at = (now_local + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        
        response = self.client.post("/api/v1/bookings/barber/", {
            "barber_id": str(self.barber.id),
            "starts_at": starts_at.isoformat(),
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking_data = response.json()
        self.assertEqual(booking_data["total_price_tiyin"], 0)
        self.assertEqual(booking_data["status"], Booking.Status.CONFIRMED)
        self.assertEqual(booking_data["barber"]["club"]["name"], "Gentleman Barbershop")
        self.assertEqual(booking_data["barber"]["full_name"], "Master Alisher")

        # Check that the slot is now unavailable
        res = get_barber_available_slots(self.barber, starts_at.date())
        slot_10 = next(s for s in res["slots"] if s["hour"] == 10)
        self.assertFalse(slot_10["is_available"])

    def test_staff_cabinet_barbers_moderation(self):
        self.client.force_authenticate(user=self.staff_admin)

        # List barbers in cabinet
        response = self.client.get("/api/v1/cabinet/barbers/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Approve pending affiliation
        new_barber_user = User.objects.create_user(
            username="pending_barber_u",
            phone="+998906666666",
        )
        new_barber = Barber.objects.create(
            user=new_barber_user,
            full_name="Pending Barber",
            club=self.barbershop,
            branch=self.branch,
            affiliation_status=Barber.AffiliationStatus.PENDING,
        )
        approve_url = f"/api/v1/cabinet/barbers/{new_barber.id}/approve-affiliation/"
        resp = self.client.post(approve_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        new_barber.refresh_from_db()
        self.assertEqual(new_barber.affiliation_status, Barber.AffiliationStatus.APPROVED)

    def test_barber_reviews_and_rating(self):
        from apps.reviews.services import refresh_barber_rating

        self.client.force_authenticate(user=self.customer)
        # Create completed booking
        booking = Booking.objects.create(
            user=self.customer,
            barber=self.barber,
            starts_at=timezone.now() - timedelta(hours=2),
            ends_at=timezone.now() - timedelta(hours=1),
            total_price_tiyin=0,
            status=Booking.Status.COMPLETED,
        )

        # Submit review
        Review.objects.create(
            user=self.customer,
            booking=booking,
            club=self.barbershop,
            barber=self.barber,
            rating=5,
            barber_rating=5,
            comment="Ajoyib usta!",
        )
        refresh_barber_rating(self.barber.id)
        self.barber.refresh_from_db()
        self.assertEqual(float(self.barber.rating), 5.0)
        self.assertEqual(self.barber.review_count, 1)
