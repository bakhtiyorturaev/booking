from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clubs.models import Branch, City, Club, District


class ClubCabinetAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username="club_owner",
            phone="+998901110001",
        )
        cls.other_user = User.objects.create_user(
            username="other_owner",
            phone="+998901110002",
        )
        cls.city = City.objects.create(name="Toshkent", slug="toshkent-test")
        cls.district = District.objects.create(
            city=cls.city,
            name="Mirobod",
            slug="mirobod-test",
        )
        cls.club = Club.objects.create(owner=cls.owner, name="Owner Club")

    def authenticated_client(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_owner_can_list_only_owned_clubs(self):
        Club.objects.create(owner=self.other_user, name="Other Club")

        response = self.authenticated_client(self.owner).get("/api/v1/cabinet/clubs/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Owner Club")

    def test_owner_can_create_branch_for_owned_club(self):
        response = self.authenticated_client(self.owner).post(
            "/api/v1/cabinet/branches/",
            {
                "club": str(self.club.id),
                "name": "Main Branch",
                "address": "Amir Temur 1",
                "city": str(self.city.id),
                "district": str(self.district.id),
                "latitude": "41.311081",
                "longitude": "69.240562",
                "status": Branch.Status.DRAFT,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Branch.objects.filter(club=self.club, name="Main Branch").exists())

    def test_other_user_cannot_create_branch_for_foreign_club(self):
        response = self.authenticated_client(self.other_user).post(
            "/api/v1/cabinet/branches/",
            {
                "club": str(self.club.id),
                "name": "Forbidden Branch",
                "address": "Amir Temur 2",
                "city": str(self.city.id),
                "district": str(self.district.id),
                "latitude": "41.311081",
                "longitude": "69.240562",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Branch.objects.filter(name="Forbidden Branch").exists())

    def test_anonymous_user_cannot_access_cabinet(self):
        response = APIClient().get("/api/v1/cabinet/clubs/")

        self.assertEqual(response.status_code, 401)


class PublicClubsAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username="public_test_owner",
            phone="+998901110099",
        )
        cls.city = City.objects.create(name="Toshkent", slug="toshkent-pub")
        cls.district = District.objects.create(
            city=cls.city,
            name="Yunusobod",
            slug="yunusobod-pub",
        )
        # Active club with active branch and zone
        cls.club1 = Club.objects.create(
            owner=cls.owner,
            name="Alpha Gaming",
            status=Club.Status.ACTIVE,
            rating="4.80",
        )
        cls.branch1 = Branch.objects.create(
            club=cls.club1,
            name="Alpha Center",
            address="Amir Temur 10",
            city=cls.city,
            district=cls.district,
            latitude="41.311081",
            longitude="69.240562",
            status=Branch.Status.ACTIVE,
        )
        from apps.clubs.models import Zone
        cls.zone1 = Zone.objects.create(
            branch=cls.branch1,
            name="VIP Room",
            price_per_hour_tiyin=5000000,
            status=Zone.Status.ACTIVE,
        )

        # Second active club
        cls.club2 = Club.objects.create(
            owner=cls.owner,
            name="Beta Arena",
            status=Club.Status.ACTIVE,
            rating="4.20",
        )
        cls.branch2 = Branch.objects.create(
            club=cls.club2,
            name="Beta Branch",
            address="Navoiy 15",
            city=cls.city,
            district=cls.district,
            latitude="41.320000",
            longitude="69.250000",
            status=Branch.Status.ACTIVE,
        )
        cls.zone2 = Zone.objects.create(
            branch=cls.branch2,
            name="Standard",
            price_per_hour_tiyin=2500000,
            status=Zone.Status.ACTIVE,
        )

    def test_list_public_clubs(self):
        client = APIClient()
        response = client.get("/api/v1/clubs/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_list_public_clubs_ordering_by_name(self):
        client = APIClient()
        response = client.get("/api/v1/clubs/?ordering=name")

        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.data["results"]]
        self.assertEqual(names, ["Alpha Gaming", "Beta Arena"])

    def test_list_public_clubs_ordering_by_price(self):
        client = APIClient()
        response = client.get("/api/v1/clubs/?ordering=price")

        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.data["results"]]
        self.assertEqual(names, ["Beta Arena", "Alpha Gaming"])

    def test_list_public_branches(self):
        client = APIClient()
        response = client.get("/api/v1/branches/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_list_public_branches_with_location_distance(self):
        client = APIClient()
        response = client.get("/api/v1/branches/?latitude=41.311081&longitude=69.240562&ordering=distance")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        # First one is exactly at the requested coordinates (distance approx 0)
        self.assertEqual(response.data["results"][0]["name"], "Alpha Center")

