"""Ommaviy katalog endpointlari (katalog, filiallar, sartaroshlar) testlari.

Qamrab olingan muammolar:
  1. `GET /api/v1/branches/?search=...` — `Q(full_address__icontains=...)`
     model maydoni emas, Python `@property` ga murojaat qiladi, shuning uchun
     `FieldError` -> 500. Qidiruv funksiyasi butunlay ishlamaydi.
  2. (TUZATILDI) `GET /api/v1/barbers/` — paginatsiya yo'q, javob butun
     jadvalni qaytaradi.
  3. Ommaviy sartarosh kartasi autentifikatsiyasiz `phone` ni oshkor qiladi.
  4. Masofa bo'yicha filtrlash/saralash butun querysetni xotiraga yuklaydi.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.clubs.models import Branch, Club, Zone
from apps.core.models import City


class PublicBranchSearchTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name="PC City", slug="pc-city")
        self.owner = User.objects.create_user(
            username="pc_owner", phone="+998907770001", role=User.Role.CLIENT
        )
        self.club = Club.objects.create(
            name="PC Club", slug="pc-club", owner=self.owner, status=Club.Status.ACTIVE
        )
        self.branch = Branch.objects.create(
            club=self.club, name="Chilonzor filiali", city=self.city,
            address="Bunyodkor 12", latitude="41.28", longitude="69.20",
            status=Branch.Status.ACTIVE,
        )
        Zone.objects.create(
            branch=self.branch, name="PC Zona", capacity=4, price_per_hour_tiyin=500_000,
            status=Zone.Status.ACTIVE,
        )
        self.api = APIClient()

    def test_branch_list_without_search_works(self):
        response = self.api.get("/api/v1/branches/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_branch_search_must_not_crash(self):
        """Regressiya: `full_address` (Python property) bo'yicha filtrlash
        `FieldError` -> 500 bergan. Endi haqiqiy maydonlar bo'yicha izlanadi."""
        response = self.api.get("/api/v1/branches/", {"search": "Chilonzor"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_branch_search_matches_address(self):
        response = self.api.get("/api/v1/branches/", {"search": "Bunyodkor"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_club_search_still_works(self):
        response = self.api.get("/api/v1/clubs/", {"search": "PC Club"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_distance_ordering_requires_coordinates(self):
        response = self.api.get("/api/v1/branches/", {"ordering": "distance"})
        self.assertEqual(response.status_code, 400)

    def test_radius_filter_requires_coordinates(self):
        response = self.api.get("/api/v1/branches/", {"radius_km": "5"})
        self.assertEqual(response.status_code, 400)


class PublicBarberCatalogTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name="PB City", slug="pb-city")
        self.owner = User.objects.create_user(
            username="pb_owner", phone="+998907780001", role=User.Role.CLIENT
        )
        self.club = Club.objects.create(
            name="PB Club", slug="pb-club", owner=self.owner,
            category=Club.Category.BARBERSHOP,
        )
        self.branch = Branch.objects.create(
            club=self.club, name="PB Branch", city=self.city, address="Addr",
            latitude="41.3", longitude="69.2",
        )
        for index in range(5):
            user = User.objects.create_user(
                username=f"pb_barber_{index}", phone=f"+99890778001{index}"
            )
            Barber.objects.create(
                user=user, full_name=f"Barber {index}", club=self.club,
                branch=self.branch, phone=f"+99891000000{index}",
                affiliation_status=Barber.AffiliationStatus.APPROVED,
            )
        self.api = APIClient()

    def test_barber_list_is_paginated(self):
        """TUZATILDI (H-6): `PublicBarberViewSet` endi `StandardPagination`
        ishlatadi, shuning uchun endpoint bazadagi barcha sartaroshlarni
        bitta javobda qaytarmaydi."""
        response = self.api.get("/api/v1/barbers/")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, dict)
        self.assertIn("count", response.data)

    def test_anonymous_barber_card_hides_personal_phone(self):
        """TUZATILDI (M-12): katalog ro'yxati (`list`) endi `phone`ni
        chiqarmaydi — ommaviy scraping imkoniyati yopildi. Bitta sartarosh
        sahifasi (`retrieve`) hamon raqamni ko'rsatadi (qasddan, "bog'lanish"
        funksiyasi uchun) — buni alohida testda tekshiramiz."""
        response = self.api.get("/api/v1/barbers/")
        self.assertEqual(response.status_code, 200)
        first = response.data[0] if isinstance(response.data, list) else response.data["results"][0]
        self.assertNotIn("phone", first)

    def test_single_barber_page_still_shows_phone_for_contact(self):
        barber = Barber.objects.first()
        response = self.api.get(f"/api/v1/barbers/{barber.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("phone", response.data)

    def test_barber_availability_is_public_and_shaped(self):
        barber = Barber.objects.first()
        response = self.api.get(f"/api/v1/barbers/{barber.id}/availability/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("slots", response.data)
        self.assertIn("is_available", response.data)

    def test_barber_availability_rejects_bad_date(self):
        barber = Barber.objects.first()
        response = self.api.get(
            f"/api/v1/barbers/{barber.id}/availability/", {"date": "23-10-2026"}
        )
        self.assertEqual(response.status_code, 400)


class PublicBranchDetailDistanceTests(TestCase):
    """`PublicBranchViewSet.get_serializer_context()` `distance_km` ni
    hisoblash uchun filialni DB'dan QAYTA o'qiyotgan edi — holbuki
    `retrieve()`/`resources()` ALLAQACHON shu filialni yuklab olgan.
    Endi masofa to'g'ridan-to'g'ri serializerda, qo'shimcha so'rovsiz
    hisoblanadi."""

    def setUp(self):
        self.city = City.objects.create(name="Dist City", slug="dist-city")
        self.owner = User.objects.create_user(
            username="dist_owner", phone="+998907770099", role=User.Role.CLIENT
        )
        self.club = Club.objects.create(
            name="Dist Club", slug="dist-club", owner=self.owner, status=Club.Status.ACTIVE
        )
        self.branch = Branch.objects.create(
            club=self.club, name="Dist filiali", city=self.city,
            address="Masofa 1", latitude="41.28", longitude="69.20",
            status=Branch.Status.ACTIVE,
        )
        self.api = APIClient()

    def test_retrieve_returns_distance_km_without_extra_branch_query(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as captured:
            response = self.api.get(
                f"/api/v1/branches/{self.branch.id}/",
                {"latitude": "41.30", "longitude": "69.21"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["distance_km"])
        self.assertGreater(response.data["distance_km"], 0)

        branch_table_queries = [
            query for query in captured.captured_queries
            if '"club_branches"' in query["sql"]
        ]
        self.assertEqual(
            len(branch_table_queries), 1,
            "Filial faqat bir marta (get_object orqali) o'qilishi kerak, distance_km uchun qaytadan emas",
        )

    def test_retrieve_without_location_has_null_distance(self):
        response = self.api.get(f"/api/v1/branches/{self.branch.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["distance_km"])


class BarberModelDefaultsTests(TestCase):
    def test_work_time_defaults_are_time_objects(self):
        """TUZATILDI (M-7): `Barber.work_start_time`/`work_end_time` endi
        `datetime.time(...)` defaultidan foydalanadi (ilgari `str` edi)."""
        import datetime

        user = User.objects.create_user(username="bm_barber", phone="+998907790001")
        barber = Barber.objects.create(user=user, full_name="BM Barber")
        self.assertIsInstance(barber.work_start_time, datetime.time)
        self.assertIsInstance(barber.work_end_time, datetime.time)
