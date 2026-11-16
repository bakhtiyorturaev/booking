"""`Branch.timezone` oddiy matn maydoni va `BranchManagementSerializer`da
hech qanday tekshiruv yo'q edi — noto'g'ri qiymat (masalan yozuvdagi xato)
saqlanib qolsa, u filialning HAR BIR keyingi bron/bo'sh vaqt so'rovida
`ZoneInfo(branch.timezone)` chaqirilgan joyda ushlanmagan xatolik (500)
sifatida chiqardi. Endi noto'g'ri vaqt mintaqasi saqlashda rad etiladi."""
from rest_framework.exceptions import ValidationError
from django.test import TestCase

from apps.clubs.serializers import BranchManagementSerializer


class BranchTimezoneValidationTests(TestCase):
    def test_rejects_unknown_timezone(self):
        serializer = BranchManagementSerializer()
        with self.assertRaises(ValidationError):
            serializer.validate_timezone("Not/A_Real_Zone")

    def test_rejects_blank_timezone(self):
        serializer = BranchManagementSerializer()
        with self.assertRaises(ValidationError):
            serializer.validate_timezone("")

    def test_accepts_valid_timezone(self):
        serializer = BranchManagementSerializer()
        self.assertEqual(serializer.validate_timezone("Asia/Tashkent"), "Asia/Tashkent")
