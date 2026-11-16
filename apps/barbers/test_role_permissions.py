"""Rollar va IDOR testlari: sartarosh / klub egasi / platforma admini.

Bu fayl ikki xil muammoni qamrab oladi:

A) IDOR himoyasi ISHLAYDI deb tasdiqlash (regressiya qulfi):
   - begona klub egasi boshqa klubning sartaroshini ko'rmaydi/tahrir qilmaydi;
   - sartarosh boshqa sartaroshning profilini ko'rmaydi.

B) Rol bo'shliqlari (gap) — `IsStaffOrReadOnly` barcha yozish amallarini
   faqat platforma adminiga ochadi, shuning uchun:
   - sartarosh o'z holatini/profilini/birikish arizasini yubora olmaydi;
   - klub egasi `require_affiliation_manager` ruxsat bergan arizani ham
     tasdiqlay olmaydi (o'lik avtorizatsiya shoxi).
"""

import unittest

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.clubs.models import Branch, Club
from apps.core.models import City


class BarberCabinetIsolationTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name="RP City", slug="rp-city")
        self.owner_a = User.objects.create_user(
            username="rp_owner_a", phone="+998906660001", role=User.Role.CLIENT
        )
        self.owner_b = User.objects.create_user(
            username="rp_owner_b", phone="+998906660002", role=User.Role.CLIENT
        )
        self.club_a = Club.objects.create(
            name="RP Club A", slug="rp-club-a", owner=self.owner_a,
            category=Club.Category.BARBERSHOP,
        )
        self.club_b = Club.objects.create(
            name="RP Club B", slug="rp-club-b", owner=self.owner_b,
            category=Club.Category.BARBERSHOP,
        )
        self.branch_a = Branch.objects.create(
            club=self.club_a, name="RP Branch A", city=self.city, address="A",
            latitude="41.3", longitude="69.2",
        )
        self.barber_user = User.objects.create_user(
            username="rp_barber", phone="+998906660003"
        )
        self.barber_a = Barber.objects.create(
            user=self.barber_user, full_name="RP Barber A", club=self.club_a,
            branch=self.branch_a, affiliation_status=Barber.AffiliationStatus.PENDING,
        )
        other_user = User.objects.create_user(
            username="rp_barber_b", phone="+998906660004"
        )
        self.barber_b = Barber.objects.create(
            user=other_user, full_name="RP Barber B", club=self.club_b,
            affiliation_status=Barber.AffiliationStatus.APPROVED,
        )
        self.admin = User.objects.create_user(
            username="rp_admin", phone="+998906660005", role=User.Role.ADMIN,
            is_staff=True, is_superuser=True,
        )

    def _client(self, user):
        api = APIClient()
        api.force_authenticate(user)
        return api

    def test_owner_sees_only_own_club_barbers(self):
        response = self._client(self.owner_a).get("/api/v1/cabinet/barbers/")
        self.assertEqual(response.status_code, 200)
        names = {item["full_name"] for item in response.data["results"]}
        self.assertEqual(names, {"RP Barber A"})

    def test_owner_cannot_retrieve_foreign_barber(self):
        response = self._client(self.owner_a).get(
            f"/api/v1/cabinet/barbers/{self.barber_b.id}/"
        )
        self.assertEqual(response.status_code, 404)

    def test_barber_sees_only_own_record(self):
        response = self._client(self.barber_user).get("/api/v1/cabinet/barbers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["results"]], [str(self.barber_a.id)]
        )

    def test_foreign_owner_cannot_approve_affiliation(self):
        response = self._client(self.owner_b).post(
            f"/api/v1/cabinet/barbers/{self.barber_a.id}/approve-affiliation/"
        )
        self.assertIn(response.status_code, (403, 404))
        self.barber_a.refresh_from_db()
        self.assertEqual(
            self.barber_a.affiliation_status, Barber.AffiliationStatus.PENDING
        )

    def test_barber_cannot_self_approve_affiliation(self):
        response = self._client(self.barber_user).post(
            f"/api/v1/cabinet/barbers/{self.barber_a.id}/approve-affiliation/"
        )
        self.assertEqual(response.status_code, 403)
        self.barber_a.refresh_from_db()
        self.assertEqual(
            self.barber_a.affiliation_status, Barber.AffiliationStatus.PENDING
        )

    def test_platform_admin_can_approve_affiliation(self):
        response = self._client(self.admin).post(
            f"/api/v1/cabinet/barbers/{self.barber_a.id}/approve-affiliation/"
        )
        self.assertEqual(response.status_code, 200)
        self.barber_a.refresh_from_db()
        self.assertEqual(
            self.barber_a.affiliation_status, Barber.AffiliationStatus.APPROVED
        )

    def test_owning_club_owner_should_be_able_to_approve_affiliation(self):
        """Regressiya: ilgari `IsStaffOrReadOnly` barcha POST'larni faqat
        platforma adminiga ochib, `require_affiliation_manager` shoxini
        yetib bo'lmas qilib qo'ygan edi."""
        response = self._client(self.owner_a).post(
            f"/api/v1/cabinet/barbers/{self.barber_a.id}/approve-affiliation/"
        )
        self.assertEqual(response.status_code, 200)


class BarberSelfServiceTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name="SS City", slug="ss-city")
        self.owner = User.objects.create_user(
            username="ss_owner", phone="+998906670001", role=User.Role.CLIENT
        )
        self.club = Club.objects.create(
            name="SS Club", slug="ss-club", owner=self.owner,
            category=Club.Category.BARBERSHOP,
        )
        self.other_club = Club.objects.create(
            name="SS Other", slug="ss-other", owner=self.owner,
            category=Club.Category.BARBERSHOP,
        )
        self.user = User.objects.create_user(username="ss_barber", phone="+998906670002")
        self.barber = Barber.objects.create(
            user=self.user, full_name="SS Barber", club=self.club,
            affiliation_status=Barber.AffiliationStatus.APPROVED,
        )
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def test_barber_can_read_own_profile(self):
        self.assertEqual(self.api.get("/api/v1/barbers/me/").status_code, 200)

    def test_barber_can_update_own_status(self):
        """Regressiya: `IsStaffOrReadOnly` sababli sartarosh o'z holatini
        o'zgartirganda 403 olardi."""
        response = self.api.post(
            "/api/v1/barbers/me/status/", {"status": "BREAK"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_barber_can_update_own_working_hours(self):
        """Regressiya: `BarberProfileAPIView.patch` ham xuddi shu sababdan
        403 berardi."""
        response = self.api.patch(
            "/api/v1/barbers/me/",
            {"work_start_time": "10:00", "work_end_time": "19:00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_barber_can_request_affiliation(self):
        """Regressiya: `BarberAffiliateAPIView` ham 403 berardi."""
        response = self.api.post(
            "/api/v1/barbers/me/affiliate/",
            {"club_id": str(self.other_club.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_profile_serializer_must_not_let_barber_switch_club(self):
        """Regressiya: `BarberProfileSerializer` `club`/`branch` ni yoza oladigan maydon
        sifatida ochib qo'ygan, `affiliation_status` esa read-only. Ruxsat
        tuzatilgandan keyin sartarosh APPROVED statusini saqlab turib boshqa
        sartaroshxonaga "ko'chib" olardi — shuning uchun maydonlar read-only
        bo'lishi shart."""
        from apps.barbers.serializers import BarberProfileSerializer

        read_only = set(BarberProfileSerializer.Meta.read_only_fields)
        writable = {
            name
            for name, field in BarberProfileSerializer().get_fields().items()
            if not field.read_only
        }
        self.assertNotIn(
            "club", writable,
            "BarberProfileSerializer `club` ni read-only qilish kerak "
            f"(hozirgi read_only_fields={sorted(read_only)})",
        )
        self.assertNotIn("branch", writable)
