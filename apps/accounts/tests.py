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
    BOT_TOKEN = "123456789:TEST_TOKEN_FOR_UNIT_TESTS_ONLY_0000"

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


class StaffPasswordAuthTests(APITestCase):
    def setUp(self):
        from datetime import timedelta
        self.staff_user = User.objects.create_user(
            username="test_admin",
            phone="+998901234599",
            password="InitialPassword123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )

    def test_staff_login_success_with_jwt_tokens(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"login": "test_admin", "password": "InitialPassword123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertIn("tokens", response.data["data"])
        self.assertIn("access", response.data["data"]["tokens"])
        self.assertIn("refresh", response.data["data"]["tokens"])
        self.assertFalse(response.data["data"]["password_expired"])

    def test_staff_login_with_phone_number(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"login": "+998 90 123 45 99", "password": "InitialPassword123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

    def test_staff_login_with_wrong_password(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"login": "test_admin", "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_customer_cannot_use_staff_login(self):
        User.objects.create_user(
            username="customer_user",
            phone="+998909876543",
            password="CustomerPass123!",
            role=User.Role.CUSTOMER,
            is_staff=False,
        )
        response = self.client.post(
            "/api/v1/auth/login/",
            {"login": "customer_user", "password": "CustomerPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "auth.staff_access_denied")

    def test_client_cannot_use_staff_portal(self):
        User.objects.create_user(
            username="venue_owner",
            phone="+998901234580",
            password="OwnerPassword123!",
            role=User.Role.CLIENT,
        )
        response = self.client.post(
            "/api/v1/auth/login/",
            {"login": "venue_owner", "password": "OwnerPassword123!", "login_type": "staff"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "auth.staff_access_denied")

    def test_client_can_use_client_portal(self):
        User.objects.create_user(
            username="venue_owner",
            phone="+998901234580",
            password="OwnerPassword123!",
            role=User.Role.CLIENT,
        )
        response = self.client.post(
            "/api/v1/auth/login/",
            {"login": "venue_owner", "password": "OwnerPassword123!", "login_type": "client"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_invalid_login_type_is_rejected(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {"login": "test_admin", "password": "InitialPassword123!", "login_type": "invalid"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_password_expired_after_30_days(self):
        from datetime import timedelta
        self.staff_user.password_changed_at = timezone.now() - timedelta(days=31)
        self.staff_user.save()

        response = self.client.post(
            "/api/v1/auth/login/",
            {"login": "test_admin", "password": "InitialPassword123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["password_expired"])

    def test_change_password_resets_expiry(self):
        from datetime import timedelta
        self.staff_user.password_changed_at = timezone.now() - timedelta(days=31)
        self.staff_user.save()

        tokens = create_auth_tokens(self.staff_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "old_password": "InitialPassword123!",
                "new_password": "NewSecurePassword456!",
                "confirm_password": "NewSecurePassword456!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])

        self.staff_user.refresh_from_db()
        self.assertTrue(self.staff_user.check_password("NewSecurePassword456!"))
        self.assertFalse(self.staff_user.is_password_expired)


@override_settings(TELEGRAM_BOT_USERNAME="rezervuz_test_bot")
class TelegramCodeAuthTests(APITestCase):
    def setUp(self):
        TelegramBotSettings.objects.update_or_create(
            pk=1,
            defaults={
                "is_enabled": True,
                "bot_token": "123456789:TEST_TOKEN_FOR_UNIT_TESTS_ONLY_0000",
                "bot_username": "rezervuz_test_bot",
            },
        )

    def test_telegram_code_init_returns_bot_url_and_session(self):
        response = self.client.post("/api/v1/auth/telegram/code/init/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        data = response.data["data"]
        self.assertIn("session_id", data)
        self.assertIn("bot_url", data)
        self.assertTrue(data["bot_url"].startswith("https://t.me/rezervuz_test_bot?start=auth_"))

    def test_telegram_code_generate_and_verify_success(self):
        from apps.accounts.services.telegram_code_auth import generate_telegram_code_for_user

        init_resp = self.client.post("/api/v1/auth/telegram/code/init/")
        session_id = init_resp.data["data"]["session_id"]

        user_info = {
            "id": 99887766,
            "first_name": "Aziz",
            "last_name": "Rahimov",
            "username": "aziz_r",
            "language_code": "uz",
        }
        code = generate_telegram_code_for_user(user_info, session_id=session_id)
        self.assertEqual(len(code), 5)
        self.assertTrue(code.isdigit())

        # Verify
        verify_resp = self.client.post(
            "/api/v1/auth/telegram/code/verify/",
            {"code": code, "session_id": session_id, "device_name": "Web Browser"},
            format="json",
        )
        self.assertEqual(verify_resp.status_code, 200)
        self.assertTrue(verify_resp.data["success"])
        self.assertIn("access", verify_resp.data["data"]["tokens"])
        self.assertEqual(verify_resp.data["data"]["user"]["telegram_user_id"], 99887766)

    def test_telegram_code_invalid_fails(self):
        response = self.client.post(
            "/api/v1/auth/telegram/code/verify/",
            {"code": "00000", "session_id": "nonexistent_session"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "auth.code_expired_or_invalid")

    def test_code_is_bound_to_browser_session_and_can_only_be_used_once(self):
        from apps.accounts.services.telegram_code_auth import generate_telegram_code_for_user
        first = self.client.post("/api/v1/auth/telegram/code/init/").data["data"]["session_id"]
        second = self.client.post("/api/v1/auth/telegram/code/init/").data["data"]["session_id"]
        code = generate_telegram_code_for_user({"id": 88881111, "first_name": "Tester"}, first)
        self.assertEqual(self.client.post("/api/v1/auth/telegram/code/verify/", {"code": code, "session_id": second}).status_code, 400)
        self.assertEqual(self.client.post("/api/v1/auth/telegram/code/verify/", {"code": code, "session_id": first}).status_code, 200)
        self.assertEqual(self.client.post("/api/v1/auth/telegram/code/verify/", {"code": code, "session_id": first}).status_code, 400)

    def test_code_expires_from_generation_and_failed_attempts_persist(self):
        from apps.accounts.services.telegram_code_auth import generate_telegram_code_for_user, session_hash
        from apps.accounts.models import TelegramLoginChallenge
        from datetime import timedelta
        session = self.client.post("/api/v1/auth/telegram/code/init/").data["data"]["session_id"]
        code = generate_telegram_code_for_user({"id": 88881112}, session)
        wrong = "00000"
        for _ in range(5):
            self.assertEqual(self.client.post("/api/v1/auth/telegram/code/verify/", {"code": wrong, "session_id": session}).status_code, 400)
        challenge = TelegramLoginChallenge.objects.get(session_hash=session_hash(session))
        self.assertEqual(challenge.attempts, 5)
        self.assertEqual(self.client.post("/api/v1/auth/telegram/code/verify/", {"code": code, "session_id": session}).status_code, 400)
        new_session = self.client.post("/api/v1/auth/telegram/code/init/").data["data"]["session_id"]
        new_code = generate_telegram_code_for_user({"id": 88881112}, new_session)
        TelegramLoginChallenge.objects.filter(session_hash=session_hash(new_session)).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.post("/api/v1/auth/telegram/code/verify/", {"code": new_code, "session_id": new_session}).status_code, 400)

    def test_bot_start_sends_code_only_in_private_chat(self):
        from telegram_bot.handlers import handle_message
        from apps.accounts.models import TelegramLoginChallenge
        session = self.client.post("/api/v1/auth/telegram/code/init/").data["data"]["session_id"]
        client = Mock()
        message = {"chat": {"id": 88881114, "type": "private"}, "from": {"id": 88881114}, "text": "/start auth_" + session}
        handle_message(client, message)
        self.assertTrue(client.send_message.called)
        self.assertIn("<b>Login code: ", client.send_message.call_args.args[1])
        self.assertNotIn("1 minute", client.send_message.call_args.args[1])
        button = client.send_message.call_args.kwargs["reply_markup"]["inline_keyboard"][0][0]
        self.assertEqual(len(button["copy_text"]["text"]), 5)
        challenge = TelegramLoginChallenge.objects.get()
        self.assertTrue(challenge.code_hash)
        second = self.client.post("/api/v1/auth/telegram/code/init/").data["data"]["session_id"]
        handle_message(client, {**message, "chat": {"id": -1001234, "type": "group"}, "text": "/start auth_" + second})
        self.assertEqual(TelegramLoginChallenge.objects.exclude(code_hash="").count(), 1)

    def test_code_status_tracks_generation_expiry_and_hides_secrets(self):
        from apps.accounts.services.telegram_code_auth import generate_telegram_code_for_user, session_hash
        from apps.accounts.models import TelegramLoginChallenge
        from datetime import timedelta
        session = self.client.post("/api/v1/auth/telegram/code/init/").data["data"]["session_id"]
        url = "/api/v1/auth/telegram/code/status/"
        response = self.client.post(url, {"session_id": session})
        self.assertEqual(response.data["data"], {"status": "waiting", "expires_in": 0})
        generate_telegram_code_for_user({"id": 88881120}, session)
        response = self.client.post(url, {"session_id": session})
        self.assertEqual(response.data["data"]["status"], "ready")
        self.assertGreater(response.data["data"]["expires_in"], 59)
        self.assertEqual(set(response.data["data"]), {"status", "expires_in"})
        self.assertEqual(self.client.post(url, {"session_id": "unknown"}).data["data"]["status"], "expired")
        TelegramLoginChallenge.objects.filter(session_hash=session_hash(session)).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.post(url, {"session_id": session}).data["data"]["status"], "expired")

    def test_repeated_start_cannot_replace_code_or_extend_expiry(self):
        from apps.accounts.services.telegram_code_auth import generate_telegram_code_for_user, TelegramCodeAuthError, session_hash
        from apps.accounts.models import TelegramLoginChallenge
        session = self.client.post("/api/v1/auth/telegram/code/init/").data["data"]["session_id"]
        code = generate_telegram_code_for_user({"id": 88881121}, session)
        challenge = TelegramLoginChallenge.objects.get(session_hash=session_hash(session))
        previous_expiry = challenge.expires_at
        previous_hash = challenge.code_hash
        with self.assertRaises(TelegramCodeAuthError):
            generate_telegram_code_for_user({"id": 88881121}, session)
        challenge.refresh_from_db()
        self.assertEqual(challenge.expires_at, previous_expiry)
        self.assertEqual(challenge.code_hash, previous_hash)
        self.assertEqual(self.client.post("/api/v1/auth/telegram/code/verify/", {"session_id": session, "code": code}).status_code, 200)
        self.assertEqual(self.client.post("/api/v1/auth/telegram/code/status/", {"session_id": session}).data["data"]["status"], "expired")

    def test_plain_start_does_not_issue_login_code(self):
        from telegram_bot.handlers import handle_message
        from apps.accounts.models import TelegramLoginChallenge
        self.client.post("/api/v1/auth/telegram/code/init/")
        client = Mock()
        handle_message(client, {"chat": {"id": 88881122, "type": "private"}, "from": {"id": 88881122}, "text": "/start"})
        self.assertFalse(TelegramLoginChallenge.objects.exclude(code_hash="").exists())
        self.assertNotIn("Login code:", str(client.send_message.call_args_list))
