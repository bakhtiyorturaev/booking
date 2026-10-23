"""`generate_booking_number()` 10 marta ketma-ket mavjud raqamga to'qnashsa,
oxirgi (hali TEKSHIRILMAGAN) raqamni jim qaytarardi — nazariy jihatdan
to'qnashgan `booking_number` bilan `IntegrityError` berishi mumkin edi. Endi
bunday holatda aniq xatolik (`RuntimeError`) ko'tariladi."""
from unittest.mock import patch

from django.test import TestCase

from apps.bookings.models import generate_booking_number


class BookingNumberGenerationTests(TestCase):
    def test_returns_unique_number_by_default(self):
        number = generate_booking_number()
        self.assertEqual(len(number), 12)
        self.assertTrue(number.isdigit())

    def test_raises_instead_of_returning_unchecked_number_on_exhaustion(self):
        with patch(
            "apps.bookings.models.Booking.objects.filter",
            return_value=type("AlwaysExists", (), {"exists": lambda self: True})(),
        ):
            with self.assertRaises(RuntimeError):
                generate_booking_number()
