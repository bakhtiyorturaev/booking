from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserProfile
from apps.barbers.models import Barber
from apps.bookings.models import Booking, Cancellation
from apps.clubs.models import Branch, City, Club, Zone


class PortalIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(username="portal_staff", telegram_user_id=9100000, role=User.Role.MODERATOR)
        cls.owner = User.objects.create_user(username="portal_owner", telegram_user_id=9100001, role=User.Role.CLIENT)
        cls.other = User.objects.create_user(username="portal_other", telegram_user_id=9100002, role=User.Role.CLIENT)
        cls.customer = User.objects.create_user(username="portal_customer", phone="+998901234560")
        UserProfile.objects.create(user=cls.customer, full_name="Booking Customer")
        cls.barber_user = User.objects.create_user(username="portal_barber", telegram_user_id=9100003, role=User.Role.CLIENT)
        cls.city = City.objects.create(name="Portal City", slug="portal-city")
        cls.clubs = []
        cls.branches = []
        cls.zones = []
        for index, owner in enumerate((cls.owner, cls.other)):
            club = Club.objects.create(owner=owner, name=f"Portal Salon {index}", category="BARBERSHOP", status="ACTIVE")
            branch = Branch.objects.create(club=club, city=cls.city, name=f"Portal Branch {index}", address="Address", latitude=41, longitude=69)
            zone = Zone.objects.create(branch=branch, name=f"Portal Zone {index}", capacity=5, price_per_hour_tiyin=10000)
            cls.clubs.append(club)
            cls.branches.append(branch)
            cls.zones.append(zone)
        cls.barber = Barber.objects.create(user=cls.barber_user, club=cls.clubs[0], branch=cls.branches[0], full_name="Portal Barber", affiliation_status="PENDING")

    def setUp(self):
        self.api = APIClient()

    def booking(self, *, zone=None, barber=None, starts_at=None):
        starts = starts_at or timezone.now() + timedelta(hours=2)
        return Booking.objects.create(user=self.customer, zone=zone, barber=barber, starts_at=starts, ends_at=starts + timedelta(hours=1), status="CONFIRMED", total_price_tiyin=10000)

    def test_owner_reads_are_limited_to_own_objects_even_with_foreign_filters(self):
        own = self.booking(zone=self.zones[0])
        foreign = self.booking(zone=self.zones[1])
        self.api.force_authenticate(self.owner)
        for endpoint, own_object, foreign_object in (
            ("clubs", self.clubs[0], self.clubs[1]),
            ("branches", self.branches[0], self.branches[1]),
            ("zones", self.zones[0], self.zones[1]),
            ("bookings", own, foreign),
            ("venue-billing", self.clubs[0], self.clubs[1]),
            ("branch-billing", self.branches[0], self.branches[1]),
        ):
            with self.subTest(endpoint=endpoint):
                response = self.api.get(f"/api/v1/cabinet/{endpoint}/")
                self.assertEqual(response.status_code, 200)
                self.assertEqual({item["id"] for item in response.data["results"]}, {str(own_object.pk)})
                self.assertEqual(self.api.get(f"/api/v1/cabinet/{endpoint}/{foreign_object.pk}/").status_code, 404)
        response = self.api.get("/api/v1/cabinet/bookings/", {"club_id": str(self.clubs[1].pk)})
        self.assertEqual(response.data["count"], 0)

    def test_owner_cannot_access_staff_controls_or_transfer_resources(self):
        self.api.force_authenticate(self.owner)
        for endpoint in ("users", "stats", "payments", "venue-payments"):
            self.assertEqual(self.api.get(f"/api/v1/cabinet/{endpoint}/").status_code, 403)
        response = self.api.patch(f"/api/v1/cabinet/branches/{self.branches[0].pk}/", {"club": str(self.clubs[1].pk)}, format="json")
        self.assertEqual(response.status_code, 403)
        response = self.api.patch(f"/api/v1/cabinet/zones/{self.zones[0].pk}/", {"branch": str(self.branches[1].pk)}, format="json")
        self.assertEqual(response.status_code, 403)
        self.branches[0].refresh_from_db()
        self.zones[0].refresh_from_db()
        self.assertEqual(self.branches[0].club_id, self.clubs[0].pk)
        self.assertEqual(self.zones[0].branch_id, self.branches[0].pk)

    def test_staff_and_owner_can_cancel_managed_bookings_but_foreign_owner_cannot(self):
        for actor in (self.staff, self.owner):
            booking = self.booking(zone=self.zones[0], starts_at=timezone.now() + timedelta(minutes=10))
            self.api.force_authenticate(self.other)
            response = self.api.post(f"/api/v1/cabinet/bookings/{booking.pk}/cancel/", {"reason": "Foreign attempt"})
            self.assertEqual(response.status_code, 403)
            booking.refresh_from_db()
            self.assertEqual(booking.status, "CONFIRMED")
            self.api.force_authenticate(actor)
            response = self.api.post(f"/api/v1/cabinet/bookings/{booking.pk}/cancel/", {"reason": "Closed for maintenance"})
            self.assertEqual(response.status_code, 200, response.data)
            booking.refresh_from_db()
            self.assertEqual(booking.status, "CANCELLED")
            self.assertEqual(Cancellation.objects.get(booking=booking).requested_by_id, actor.pk)

    def test_standalone_barber_can_cancel_own_appointments_only(self):
        self.barber.club = None
        self.barber.branch = None
        self.barber.save()
        appointment = self.booking(barber=self.barber)
        foreign = self.booking(zone=self.zones[1])
        self.api.force_authenticate(self.barber_user)
        self.assertEqual(self.api.post(f"/api/v1/cabinet/bookings/{foreign.pk}/cancel/").status_code, 403)
        self.assertEqual(self.api.post(f"/api/v1/cabinet/bookings/{appointment.pk}/cancel/").status_code, 200)

    def test_booking_customer_details_are_available_only_in_authorized_cabinet(self):
        booking = self.booking(zone=self.zones[0])
        self.api.force_authenticate(self.owner)
        response = self.api.get(f"/api/v1/cabinet/bookings/{booking.pk}/")
        self.assertEqual(response.data["user"]["full_name"], "Booking Customer")
        self.assertEqual(response.data["user"]["phone"], self.customer.phone)
        self.api.force_authenticate(self.other)
        self.assertEqual(self.api.get(f"/api/v1/cabinet/bookings/{booking.pk}/").status_code, 404)
        self.api.force_authenticate(self.customer)
        self.assertNotIn("user", self.api.get(f"/api/v1/bookings/{booking.pk}/").data)

    def test_affiliation_permissions_match_owner_and_barber_roles(self):
        for actor, allowed in ((self.staff, True), (self.owner, True), (self.barber_user, False)):
            self.api.force_authenticate(actor)
            response = self.api.get(f"/api/v1/cabinet/barbers/{self.barber.pk}/")
            self.assertEqual(response.data["can_manage_affiliation"], allowed)
        self.api.force_authenticate(self.barber_user)
        self.assertEqual(self.api.post(f"/api/v1/cabinet/barbers/{self.barber.pk}/approve-affiliation/").status_code, 403)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.post(f"/api/v1/cabinet/barbers/{self.barber.pk}/approve-affiliation/").status_code, 200)

    def test_barber_search_status_and_pagination_work_together(self):
        self.barber.status = "BREAK"
        self.barber.phone = "+998901112233"
        self.barber.save()
        for index in range(22):
            account = User.objects.create_user(username=f"extra_barber_{index}", telegram_user_id=9200000 + index)
            Barber.objects.create(user=account, club=self.clubs[0], branch=self.branches[0], full_name=f"Extra Barber {index}", status="AVAILABLE")
        self.api.force_authenticate(self.owner)
        first = self.api.get("/api/v1/cabinet/barbers/", {"page_size": 20})
        second = self.api.get("/api/v1/cabinet/barbers/", {"page_size": 20, "page": 2})
        self.assertEqual(first.data["count"], 23)
        self.assertEqual(len(first.data["results"]), 20)
        self.assertEqual(len(second.data["results"]), 3)
        self.assertTrue(first.data["next"])
        self.assertFalse(set(item["id"] for item in first.data["results"]) & set(item["id"] for item in second.data["results"]))
        filtered = self.api.get("/api/v1/cabinet/barbers/", {"status": "BREAK", "query": "1112233"})
        self.assertEqual(filtered.data["count"], 1)
        self.assertEqual(filtered.data["results"][0]["id"], str(self.barber.pk))

    def test_invalid_cabinet_filters_return_validation_errors(self):
        self.api.force_authenticate(self.owner)
        for params in ({"date": "broken"}, {"branch_id": "broken"}, {"club_id": "broken"}, {"barber_id": "broken"}):
            self.assertEqual(self.api.get("/api/v1/cabinet/bookings/", params).status_code, 400)
        self.assertEqual(self.api.get("/api/v1/cabinet/barbers/", {"club_id": "broken"}).status_code, 400)

    def test_legacy_customer_role_owner_can_login_to_client_portal(self):
        self.owner.role = User.Role.CUSTOMER
        self.owner.set_password("LegacyOwnerPassword!7284")
        self.owner.save()
        response = self.api.post("/api/v1/auth/login/", {"login": self.owner.username, "password": "LegacyOwnerPassword!7284", "login_type": "client"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["user"]["has_owned_clubs"])
        self.assertFalse(response.data["data"]["user"]["has_barber_profile"])

    def test_booking_pagination_respects_page_size(self):
        for index in range(23):
            self.booking(zone=self.zones[0], starts_at=timezone.now() + timedelta(hours=index + 2))
        self.api.force_authenticate(self.owner)
        first = self.api.get("/api/v1/cabinet/bookings/", {"page_size": 20})
        second = self.api.get("/api/v1/cabinet/bookings/", {"page_size": 20, "page": 2})
        self.assertEqual(first.data["count"], 23)
        self.assertEqual(len(first.data["results"]), 20)
        self.assertEqual(len(second.data["results"]), 3)
    def test_customer_and_client_lists_are_separate_and_never_show_staff(self):
        self.api.force_authenticate(self.staff)
        hidden = [
            self.staff,
            User.objects.create_user(username="hidden_admin", telegram_user_id=9300001, role="ADMIN"),
            User.objects.create_user(username="hidden_staff_customer", telegram_user_id=9300002, role="CUSTOMER", is_staff=True),
            User.objects.create_user(username="hidden_super_client", telegram_user_id=9300003, role="CLIENT", is_superuser=True),
        ]
        for audience, expected in (("customers", {str(self.customer.pk)}), ("clients", {str(self.owner.pk), str(self.other.pk), str(self.barber_user.pk)})):
            response = self.api.get("/api/v1/cabinet/users/", {"audience": audience})
            self.assertEqual(response.status_code, 200)
            self.assertEqual({item["id"] for item in response.data["results"]}, expected)
        for account in hidden:
            self.assertEqual(self.api.get(f"/api/v1/cabinet/users/{account.pk}/").status_code, 404)
        response = self.api.get("/api/v1/cabinet/users/", {"role": "ADMIN"})
        self.assertEqual(response.data["count"], 0)

    def test_legacy_owner_is_in_client_list_once_and_not_customer_list(self):
        self.owner.role = "CUSTOMER"
        self.owner.save()
        Club.objects.create(owner=self.owner, name="Another owned venue")
        self.api.force_authenticate(self.staff)
        response = self.api.get("/api/v1/cabinet/users/", {"audience": "clients", "query": self.owner.username})
        self.assertEqual(response.data["count"], 1)
        response = self.api.get("/api/v1/cabinet/users/", {"audience": "customers", "query": self.owner.username})
        self.assertEqual(response.data["count"], 0)
