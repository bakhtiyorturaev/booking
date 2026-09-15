import hashlib
import hmac
import json
import time
import urllib.parse
from unittest.mock import Mock, patch

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User, UserProfile, UserSession
from apps.accounts.services.auth_tokens import create_auth_tokens
from apps.accounts.services.telegram_web_login import confirm_web_login_from_bot
from telegram_bot.models import TelegramBotSettings


class TelegramMiniAppAuthTests(APITestCase):
    BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"

    def setUp(self):
        TelegramBotSettings.objects.update_or_create(
            pk=1,
            defaults={
                "is_enabled": True,
                "bot_token": self.BOT_TOKEN,
            },
        )

    def _generate_init_data(self, user_dict, auth_date=None, tamper_hash=False):
        auth_date = auth_date if auth_date is not None else int(time.time())
        data = {
            "auth_date": str(auth_date),
            "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
            "user": json.dumps(user_dict, separators=(",", ":")),
        }
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret_key = hmac.new(b"WebAppData", self.BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
        hash_val = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        if tamper_hash:
            hash_val = "0000000000000000000000000000000000000000000000000000000000000000"
        data["hash"] = hash_val
        return urllib.parse.urlencode(data)

    def test_telegram_miniapp_creates_new_user_and_authenticates(self):
        user_info = {
            "id": 88776655,
            "first_name": "Jasur",
            "last_name": "Karimov",
            "username": "jasur_k",
            "language_code": "uz",
        }
        init_data = self._generate_init_data(user_info)

        response = self.client.post(
            "/api/v1/auth/telegram-miniapp/",
            {"init_data": init_data, "device_name": "Telegram WebApp Mobile"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["data"]["is_new_user"])
        self.assertIn("tokens", response.data["data"])
        self.assertIn("access", response.data["data"]["tokens"])

        created_user = User.objects.get(telegram_user_id=88776655)
        self.assertEqual(created_user.profile.full_name, "Jasur Karimov")
        self.assertEqual(created_user.profile.telegram_chat_id, "88776655")

    def test_telegram_miniapp_logs_in_existing_user(self):
        existing_user = User.objects.create_user(
            username="jasur_existing",
            telegram_user_id=99112233,
            phone="+998909998877",
        )

        user_info = {
            "id": 99112233,
            "first_name": "Jasur",
            "last_name": "Updated",
            "username": "jasur_tg",
        }
        init_data = self._generate_init_data(user_info)

        response = self.client.post(
            "/api/v1/auth/telegram-miniapp/",
            {"init_data": init_data},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["data"]["is_new_user"])
        self.assertEqual(response.data["data"]["user"]["id"], str(existing_user.id))

    def test_telegram_miniapp_rejects_forged_hash(self):
        user_info = {"id": 12345678, "first_name": "Hacker"}
        init_data = self._generate_init_data(user_info, tamper_hash=True)

        response = self.client.post(
            "/api/v1/auth/telegram-miniapp/",
            {"init_data": init_data},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_telegram_miniapp_rejects_expired_auth_date(self):
        user_info = {"id": 12345678, "first_name": "OldUser"}
        expired_date = int(time.time()) - 200000  # > 24 hours ago
        init_data = self._generate_init_data(user_info, auth_date=expired_date)

        response = self.client.post(
            "/api/v1/auth/telegram-miniapp/",
            {"init_data": init_data},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_telegram_contact_saves_phone_number(self):
        user = User.objects.create_user(
            username="contact_user",
            telegram_user_id=77665544,
        )
        self.client.force_authenticate(user)

        response = self.client.post(
            "/api/v1/auth/telegram-miniapp/contact/",
            {"phone": "+998901234567"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.phone, "+998901234567")
        self.assertTrue(user.is_phone_verified)

    def test_telegram_web_login_flow(self):
        # 1. Web client initiates login
        init_response = self.client.post("/api/v1/auth/telegram-web/init/", format="json")
        self.assertEqual(init_response.status_code, 200)
        token = init_response.data["data"]["token"]
        self.assertTrue(token)

        # 2. Check status while pending
        check_pending = self.client.get(f"/api/v1/auth/telegram-web/check/{token}/")
        self.assertEqual(check_pending.status_code, 200)
        self.assertEqual(check_pending.data["data"]["status"], "PENDING")

        # 3. User clicks link in bot
        user_info = {
            "id": 55443322,
            "first_name": "Web",
            "last_name": "User",
            "username": "web_tg_user",
        }
        confirmed = confirm_web_login_from_bot(token, user_info)
        self.assertTrue(confirmed)

        # 4. Web client polls and receives JWT tokens
        check_success = self.client.get(f"/api/v1/auth/telegram-web/check/{token}/")
        self.assertEqual(check_success.status_code, 200)
        self.assertEqual(check_success.data["data"]["status"], "SUCCESS")
        self.assertIn("tokens", check_success.data["data"])
        self.assertIn("access", check_success.data["data"]["tokens"])

    def test_token_refresh_and_logout(self):
        user = User.objects.create_user(
            username="session_user",
            telegram_user_id=11223344,
            phone="+998901112233",
        )
        tokens = create_auth_tokens(user)

        # Refresh
        refresh_resp = self.client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_resp.status_code, 200)
        self.assertIn("access", refresh_resp.data["data"]["tokens"])

        # Logout
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        logout_resp = self.client.post("/api/v1/auth/logout/", format="json")
        self.assertEqual(logout_resp.status_code, 200)
