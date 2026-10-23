"""M-14: `get_barber_available_slots` oldindan bron qilish muddati
cheklovini (`advance_booking_days`) faqat filialga biriktirilgan
sartaroshlar uchun tekshirardi (`barber.branch.advance_booking_days`
orqali) — mustaqil (filialsiz) sartaroshlar uchun bu tekshiruv butunlay
yo'q edi, demak ularga istalgan kelajakdagi sanaga bron qilish mumkin
bo'lib qolardi. Endi mustaqil sartaroshlar uchun
`STANDALONE_ADVANCE_BOOKING_DAYS` qo'llaniladi."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.barbers.models import Barber
from apps.barbers.services import get_barber_available_slots
from apps.bookings.services import STANDALONE_ADVANCE_BOOKING_DAYS
from apps.clubs.models import Club


class StandaloneBarberAdvanceBookingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="sa_owner", phone="+998901280001", role=User.Role.CLIENT)
        self.club = Club.objects.create(
            name="SA Barbershop", slug="sa-barbershop",
            category=Club.Category.BARBERSHOP, owner=self.owner, status=Club.Status.ACTIVE,
        )
        barber_user = User.objects.create_user(username="sa_barber", phone="+998901280002")
        self.barber = Barber.objects.create(
            user=barber_user, full_name="SA Barber", club=self.club,
            affiliation_status=Barber.AffiliationStatus.APPROVED, is_active=True,
        )

    def test_date_within_window_is_allowed(self):
        target_date = timezone.localdate() + timedelta(days=STANDALONE_ADVANCE_BOOKING_DAYS - 1)
        result = get_barber_available_slots(self.barber, target_date)
        self.assertNotEqual(result["reason"], "Bron sanasi ruxsat etilgan muddatdan tashqarida.")

    def test_date_far_in_the_future_is_rejected(self):
        target_date = timezone.localdate() + timedelta(days=STANDALONE_ADVANCE_BOOKING_DAYS + 5)
        result = get_barber_available_slots(self.barber, target_date)
        self.assertFalse(result["is_available"])
        self.assertEqual(result["reason"], "Bron sanasi ruxsat etilgan muddatdan tashqarida.")
        self.assertEqual(result["slots"], [])
