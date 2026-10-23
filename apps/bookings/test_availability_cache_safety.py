"""M-6: `get_branch_availability` keshga to'g'ridan-to'g'ri `Zone` model
instansiyasini (pickle qilingan holda) saqlardi. Bu xavfli: deploy orasida
model sxemasi o'zgarsa unpickle xatosi berishi mumkin, shuningdek keshning
o'zi qanday maydonlarni "muzlatib qo'yayotgani" noaniq edi. Endi faqat
kerakli maydonlarni o'z ichiga olgan oddiy dict saqlanadi."""
from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.services import get_branch_availability
from apps.clubs.models import Branch, City, Club, Zone


class AvailabilityCacheDoesNotPickleModelsTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name="AC City", slug="ac-city")
        self.owner = User.objects.create_user(
            username="ac_owner", phone="+998901250001", role=User.Role.CLIENT,
        )
        self.club = Club.objects.create(
            name="AC Club", slug="ac-club", owner=self.owner, status=Club.Status.ACTIVE,
        )
        self.branch = Branch.objects.create(
            club=self.club, name="AC Branch", city=self.city, address="Addr",
            latitude="41.0", longitude="69.0", status=Branch.Status.ACTIVE, is_24_hours=True,
        )
        self.zone = Zone.objects.create(
            branch=self.branch, name="AC Zone", capacity=2,
            booking_type=Zone.BookingType.PER_SEAT, unit_count=2,
            price_per_hour_tiyin=20_000, status=Zone.Status.ACTIVE,
        )
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.target_date = tomorrow

    def test_cached_zone_entry_is_a_plain_dict_not_a_model_instance(self):
        result = get_branch_availability(self.branch, self.target_date)
        self.assertTrue(result)
        zone_entry = result[0]["zone"]
        self.assertIsInstance(zone_entry, dict)
        self.assertNotIsInstance(zone_entry, Zone)
        self.assertEqual(zone_entry["id"], self.zone.id)
        self.assertEqual(zone_entry["name"], "AC Zone")
        self.assertEqual(zone_entry["price_per_hour_tiyin"], 20_000)

    def test_cache_hit_returns_the_same_plain_shape(self):
        first = get_branch_availability(self.branch, self.target_date)
        second = get_branch_availability(self.branch, self.target_date)
        self.assertIsInstance(second[0]["zone"], dict)
        self.assertEqual(first[0]["zone"], second[0]["zone"])
