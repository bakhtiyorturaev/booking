from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import AppTranslation


class AppTranslationTests(TestCase):
    def test_seed_and_return_requested_language(self):
        call_command("seed_app_translations", verbosity=0)

        response = APIClient().get("/api/v1/", {"lang": "ru"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["language"], "ru")
        self.assertEqual(
            response.data["translations"]["common.backend_connected"],
            "Соединение с сервером работает.",
        )
        self.assertEqual(
            AppTranslation.objects.filter(code__in=("common.backend_connected", "auth.phone_number", "common.back")).count(),
            3,
        )

    def test_normalize_language_complex_headers(self):
        from apps.core.models import normalize_language
        self.assertEqual(normalize_language("uz,uz;q=0.9"), "uz")
        self.assertEqual(normalize_language("uz, ru;q=0.8"), "uz")
        self.assertEqual(normalize_language("ru-RU,ru;q=0.9"), "ru")
        self.assertEqual(normalize_language("en-US"), "en")
        self.assertEqual(normalize_language("de,fr;q=0.9"), "uz")
        self.assertEqual(normalize_language(""), "uz")
        self.assertEqual(normalize_language(None), "uz")
