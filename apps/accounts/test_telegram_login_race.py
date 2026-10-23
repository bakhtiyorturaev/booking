"""M-13: ikki parallel `login_with_telegram_miniapp()` chaqiruvi bir xil
yangi Telegram foydalanuvchisi uchun bir vaqtda ishga tushsa (masalan, Mini
App'da tugma ikki marta tez bosilsa), ikkinchisi `telegram_user_id` unique
cheklovida `IntegrityError` (500) berardi — chunki `select_for_update()`
hali mavjud bo'lmagan qatorni qulflay olmaydi. Endi bu holat ushlanadi va
g'olib yaratgan foydalanuvchi qaytariladi.

Bu test atayin `verify_telegram_webapp_init_data`ni mocklaydi: HMAC imzo
tekshiruvi va H-8'ning bir martalik `hash` nonce keshi (`cache.add()`) bu
yerda tekshirilayotgan narsa emas — ular allaqachon
`test_auth_hardening.py`/`test_telegram_auth_security.py`da qamrab olingan.
Bundan tashqari, SQLite'ning `DatabaseCache`'i haqiqiy ikki-thread
yozishida vaqti-vaqti bilan "database is locked" xatosini jim qoldirib,
`cache.add()`dan noto'g'ri `False` qaytaradi (Django manbasidagi
`except DatabaseError: return False` izohiga qarang) — bu H-8 nonce
tekshiruvini mock qilmasak, aynan M-13 uchun yozilgan testni soxta
"allaqachon ishlatilgan" xatosi bilan beqaror qilib qo'yardi."""
import threading
import time as time_module
from unittest.mock import patch

from django.db import OperationalError
from django.test import TransactionTestCase

from apps.accounts.models import User
from apps.accounts.services.telegram_miniapp import login_with_telegram_miniapp
from telegram_bot.models import TelegramBotSettings

BOT_TOKEN = "123456:RACE-TEST-TOKEN"


class TelegramMiniAppLoginRaceTests(TransactionTestCase):
    def setUp(self):
        TelegramBotSettings.objects.update_or_create(
            pk=1, defaults={"is_enabled": True, "bot_token": BOT_TOKEN},
        )

    def test_concurrent_first_login_does_not_crash_and_creates_one_user(self):
        telegram_id = 991234567
        fake_validated_data = {"user_data": {"id": telegram_id, "first_name": "Race"}}
        results = {}
        errors = {}
        barrier = threading.Barrier(2, timeout=10)

        def attempt(label):
            try:
                barrier.wait()
                for attempt_index in range(25):
                    try:
                        with patch(
                            "apps.accounts.services.telegram_miniapp.verify_telegram_webapp_init_data",
                            return_value=fake_validated_data,
                        ):
                            results[label] = login_with_telegram_miniapp("irrelevant", bot_token=BOT_TOKEN)
                        return
                    except OperationalError as error:
                        # SQLite butun faylni yozish uchun qulflaydi — real
                        # ishlab chiqarishda (Postgres) bo'lmaydigan, faqat
                        # test muhitiga xos vaqtinchalik holat.
                        if "locked" not in str(error).lower():
                            raise
                        time_module.sleep(0.01 * (attempt_index + 1))
            except Exception as error:
                errors[label] = error

        threads = [threading.Thread(target=attempt, args=(label,)) for label in ("a", "b")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.assertEqual(errors, {}, f"Kutilmagan xatolar: {errors}")
        self.assertEqual(len(results), 2)
        self.assertEqual(results["a"]["user"].id, results["b"]["user"].id)
        self.assertEqual(User.objects.filter(telegram_user_id=telegram_id).count(), 1)
