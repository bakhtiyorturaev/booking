"""Autentifikatsiya qattiqlashtirish (hardening) testlari.

`test_telegram_auth_security.py` allaqachon imzo (hash) tekshiruvini qamrab
olgan. Bu fayl undan farqli ravishda **oqim mantiqidagi** zaifliklarni
tekshiradi:

  1. (TUZATILDI) `/start login_<token>` deep-link session fixation oqimi
     butunlay olib tashlandi — endi shu holat qayd etiladi.
  2. (TUZATILDI) Mini App `initData` replay oynasi (edi 24 soat, nonce yo'q).
  3. (TUZATILDI) Profil PATCH orqali tasdiqlanmagan telefonni "tasdiqlangan"
     qilib ko'rsatish.
  4. (TUZATILDI) Telegram botiga boshqa odamning kontaktini yuborib, uning
     raqamini o'z akkauntiga bog'lash.
  5. (TUZATILDI) `phone_verified_at` maydoni qaytarildi — Telegram OAuth
     login (`login_with_telegram`) endi 500 bermaydi.
  6. (TUZATILDI) Parol o'zgartirilganda eski sessiyalar bekor qilinmaydi;
     refresh token rotatsiyalanmaydi.
"""

import hashlib
import hmac
import json
import time
import urllib.parse

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, UserSession
from apps.accounts.services.telegram_miniapp import (
    TelegramMiniAppError,
    login_with_telegram_miniapp,
)

BOT_TOKEN = "123456:HARDENING-TEST-TOKEN"


def build_init_data(telegram_id, age_seconds=0, bot_token=BOT_TOKEN):
    fields = {
        "auth_date": str(int(time.time()) - age_seconds),
        "query_id": "AAEBAgMEBQ",
        "user": json.dumps({"id": telegram_id, "first_name": "Test"}),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode({**fields, "hash": signature})


class TelegramWebLoginDeepLinkRemovedTests(TestCase):
    """Session fixation zaifligini ochib turgan `/start login_<token>` oqimi
    butunlay olib tashlandi (`apps.accounts.services.telegram_web_login` dan
    `init_web_login` / `confirm_web_login_from_bot` / `check_web_login_status`
    o'chirildi, bot endi shu havolani eskirgan deb ko'rsatadi, ularning
    endpointlari ham urls.py'dan olib tashlandi). Bu testlar regressiya
    qulfi: funksiyalar tasodifan qaytarilib qolmasligini tekshiradi."""

    def test_vulnerable_functions_no_longer_exist(self):
        from apps.accounts.services import telegram_web_login

        for name in ("init_web_login", "confirm_web_login_from_bot", "check_web_login_status"):
            self.assertFalse(
                hasattr(telegram_web_login, name),
                f"{name} qayta qo'shilgan — session fixation zaifligi qaytadi.",
            )

    def test_deep_link_urls_are_not_routed(self):
        from django.urls import NoReverseMatch, reverse

        with self.assertRaises(NoReverseMatch):
            reverse("accounts:telegram-web-init")
        with self.assertRaises(NoReverseMatch):
            reverse("accounts:telegram-web-check", kwargs={"token": "x"})

    def test_bot_tells_user_the_link_is_outdated(self):
        from telegram_bot.handlers import handle_message

        sent = {}

        class DummyClient:
            def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
                sent["text"] = text
                return {"message_id": 1}

        handle_message(
            DummyClient(),
            {
                "chat": {"id": 990001, "type": "private"},
                "from": {"id": 990001, "first_name": "X", "language_code": "uz"},
                "text": "/start login_some-stale-token",
            },
        )
        self.assertIn("eskirgan", sent.get("text", ""))


class MiniAppReplayWindowTests(TestCase):
    def test_signature_from_a_different_token_is_rejected(self):
        init_data = build_init_data(880101, bot_token="999:WRONG-TOKEN")
        with self.assertRaises(TelegramMiniAppError):
            login_with_telegram_miniapp(init_data, bot_token=BOT_TOKEN)

    def test_future_auth_date_is_rejected(self):
        init_data = build_init_data(880102, age_seconds=-3600)
        with self.assertRaises(TelegramMiniAppError):
            login_with_telegram_miniapp(init_data, bot_token=BOT_TOKEN)

    def test_initdata_older_than_five_minutes_should_be_rejected(self):
        """TUZATILDI (H-8): `verify_telegram_webapp_init_data` endi standart
        bo'yicha 300 soniyalik oyna ishlatadi (ilgari 24 soat edi)."""
        init_data = build_init_data(880103, age_seconds=600)
        with self.assertRaises(TelegramMiniAppError):
            login_with_telegram_miniapp(init_data, bot_token=BOT_TOKEN)

    def test_same_initdata_cannot_be_replayed(self):
        """TUZATILDI (H-8): bir xil `initData` endi ikkinchi marta qabul
        qilinmaydi — `hash` qiymati cache orqali bir martalik nonce sifatida
        belgilanadi."""
        init_data = build_init_data(880104)
        login_with_telegram_miniapp(init_data, bot_token=BOT_TOKEN)
        with self.assertRaises(TelegramMiniAppError):
            login_with_telegram_miniapp(init_data, bot_token=BOT_TOKEN)


class PhoneVerifiedAtFieldRestoredTests(TestCase):
    """C-2: `0007_telegram_only_auth` migratsiyasi `User.phone_verified_at`
    ni o'chirib yuborgan, `login_with_telegram` esa hali ham uni yozar edi —
    natijada Telegram OAuth login har doim 500 berardi. Maydon qaytarildi."""

    def test_user_model_has_phone_verified_at(self):
        field_names = {
            field.name for field in User._meta.get_fields() if hasattr(field, "attname")
        }
        self.assertIn("phone_verified_at", field_names)

    def test_saving_phone_verified_at_no_longer_raises(self):
        user = User.objects.create_user(username="pva_user", phone="+998904470001")
        user.phone_verified_at = timezone.now()
        user.save(
            update_fields=(
                "phone", "phone_verified_at", "telegram_user_id",
                "telegram_verified_at", "updated_at",
            )
        )
        user.refresh_from_db()
        self.assertIsNotNone(user.phone_verified_at)

    def test_is_phone_verified_requires_phone_verified_at_not_telegram_link(self):
        """Telegram akkaunt bog'langani raqam tasdiqlanganini bildirmaydi."""
        user = User.objects.create_user(
            username="pva_user2", phone="+998904470002",
            telegram_user_id=990101, telegram_verified_at=timezone.now(),
        )
        self.assertFalse(user.is_phone_verified)
        user.phone_verified_at = timezone.now()
        user.save(update_fields=["phone_verified_at"])
        self.assertTrue(user.is_phone_verified)


class PhoneVerificationIntegrityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pv_user", phone="+998904450001", telegram_user_id=880201,
        )
        now = timezone.now()
        User.objects.filter(pk=self.user.pk).update(
            telegram_verified_at=now, phone_verified_at=now,
        )
        self.user.refresh_from_db()
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.user)

    def test_self_service_phone_change_should_drop_verified_flag(self):
        """Regressiya: ilgari `UserProfileUpdateSerializer.update` foydalanuvchi
        kiritgan har qanday raqamni saqlab, `phone_verified_at` ni tozalamagan —
        natijada `is_phone_verified` tasdiqlanmagan raqam uchun ham True
        bo'lib qolardi."""
        response = self.client_api.patch(
            "/api/v1/auth/me/", {"phone": "+998904459999"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "+998904459999")
        self.assertFalse(self.user.is_phone_verified)

    def test_contact_without_user_id_should_not_be_trusted(self):
        """Regressiya: ilgari `contact.user_id` bo'lmasa ham raqam saqlanardi —
        foydalanuvchi telefon kitobidan boshqa odamning kontaktini yuborib,
        uning raqamini o'z akkauntiga bog'lab olishi mumkin edi."""
        from telegram_bot.handlers import handle_message

        class DummyClient:
            def send_message(self, *args, **kwargs):
                return {"message_id": 1}

        handle_message(
            DummyClient(),
            {
                "chat": {"id": 880201, "type": "private"},
                "from": {"id": 880201, "first_name": "PV", "language_code": "uz"},
                "contact": {"phone_number": "+998904458888"},
            },
        )
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.phone, "+998904458888")


class PasswordChangeSessionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pwd_user", phone="+998904460001", role=User.Role.ADMIN,
            is_staff=True,
        )
        self.user.set_password("OldPassw0rd!")
        self.user.save()

    def test_password_change_should_revoke_other_sessions(self):
        """TUZATILDI (H-9): `change_user_password` endi yangi sessiyadan
        boshqa barcha eski sessiyalarni (jumladan o'g'irlangan refresh
        tokenga tegishli bo'lganini) bekor qiladi."""
        from apps.accounts.services.auth_tokens import create_auth_tokens
        from apps.accounts.services.password_auth import change_user_password

        stolen = create_auth_tokens(self.user, device_name="attacker")
        change_user_password(self.user, "OldPassw0rd!", "BrandNewPassw0rd!")
        session = UserSession.objects.get(pk=stolen["session_id"])
        self.assertIsNotNone(session.revoked_at)

    def test_refresh_token_rotates_and_detects_reuse(self):
        """TUZATILDI (H-9): har bir `refresh_auth_tokens()` chaqiruvi yangi
        `refresh` token qaytaradi; eski (allaqachon rotatsiyalangan) tokenni
        qayta ishlatishga urinish butun sessiyani bekor qiladi."""
        from apps.accounts.services.auth_tokens import (
            AuthTokenError,
            create_auth_tokens,
            refresh_auth_tokens,
        )

        tokens = create_auth_tokens(self.user, device_name="device-a")
        first_refresh = tokens["refresh"]

        rotated = refresh_auth_tokens(first_refresh)
        self.assertNotEqual(rotated["refresh"], first_refresh)

        with self.assertRaises(AuthTokenError) as error:
            refresh_auth_tokens(first_refresh)
        self.assertEqual(error.exception.code, "auth.session_revoked_token_reused")

        session = UserSession.objects.get(pk=tokens["session_id"])
        self.assertIsNotNone(session.revoked_at)

        with self.assertRaises(AuthTokenError):
            refresh_auth_tokens(rotated["refresh"])

    def test_wrong_old_password_is_rejected(self):
        from apps.accounts.services.password_auth import (
            PasswordAuthError,
            change_user_password,
        )

        with self.assertRaises(PasswordAuthError):
            change_user_password(self.user, "WrongOne!", "BrandNewPassw0rd!")
