"""Security regression tests for Telegram-based authentication.

Covers the two properties explicitly at risk in this area:
1. HMAC-SHA256 signature verification on Mini App initData
   (apps/accounts/services/telegram_miniapp.py::verify_telegram_webapp_init_data)
   must reject any tampered payload and any payload signed with the wrong
   bot token, and must reject stale auth_date (replay via an old payload).
2. The one-time login code challenge
   (apps/accounts/services/telegram_code_auth.py) must not be usable twice
   -- a second verify_telegram_code() call with the same code must fail,
   proving single_use_telegram_login_challenges is actually enforced.
"""

import hashlib
import hmac
import json
import time
import urllib.parse

from django.test import TestCase

from apps.accounts.models import User
from apps.accounts.services.telegram_code_auth import (
    generate_telegram_code_for_user,
    init_telegram_code_session,
    verify_telegram_code,
)
from apps.accounts.services.telegram_miniapp import (
    TelegramMiniAppError,
    login_with_telegram_miniapp,
    verify_telegram_webapp_init_data,
)
from telegram_bot.models import TelegramBotSettings


BOT_TOKEN = "123456:QA-TEST-BOT-TOKEN"


def _sign_init_data(fields, bot_token=BOT_TOKEN):
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()


def _build_init_data(user_id=777001, auth_date=None, bot_token=BOT_TOKEN, bad_hash=False):
    auth_date = auth_date if auth_date is not None else int(time.time())
    user_json = json.dumps({"id": user_id, "first_name": "QA", "username": "qa_tg_user"})
    fields = {"auth_date": str(auth_date), "user": user_json, "query_id": "AAQAQA"}
    computed_hash = _sign_init_data(fields, bot_token=bot_token)
    fields["hash"] = "0" * 64 if bad_hash else computed_hash
    return urllib.parse.urlencode(fields)


class TelegramMiniAppSignatureTests(TestCase):
    def setUp(self):
        TelegramBotSettings.objects.update_or_create(
            pk=1, defaults={"is_enabled": True, "bot_token": BOT_TOKEN},
        )

    def test_valid_signature_is_accepted(self):
        init_data = _build_init_data()
        validated = verify_telegram_webapp_init_data(init_data, bot_token=BOT_TOKEN)
        self.assertEqual(validated["user_data"]["id"], 777001)

    def test_tampered_hash_is_rejected(self):
        init_data = _build_init_data(bad_hash=True)
        with self.assertRaises(TelegramMiniAppError):
            verify_telegram_webapp_init_data(init_data, bot_token=BOT_TOKEN)

    def test_signature_from_wrong_bot_token_is_rejected(self):
        init_data = _build_init_data(bot_token="999999:some-other-bot-token")
        with self.assertRaises(TelegramMiniAppError):
            verify_telegram_webapp_init_data(init_data, bot_token=BOT_TOKEN)

    def test_stale_auth_date_is_rejected(self):
        stale_auth_date = int(time.time()) - 3 * 86400  # 3 kun oldin
        init_data = _build_init_data(auth_date=stale_auth_date)
        with self.assertRaises(TelegramMiniAppError):
            verify_telegram_webapp_init_data(init_data, bot_token=BOT_TOKEN, max_age_seconds=86400)

    def test_tampered_payload_with_correct_hash_for_different_data_is_rejected(self):
        """An attacker who edits any field (e.g. swapping the Telegram user id)
        without re-signing must be rejected, even though *a* valid hash is present."""
        fields = {"auth_date": str(int(time.time())), "user": json.dumps({"id": 1, "first_name": "A"})}
        fields["hash"] = _sign_init_data(fields)
        fields["user"] = json.dumps({"id": 2, "first_name": "Attacker"})  # mutate after signing
        init_data = urllib.parse.urlencode(fields)
        with self.assertRaises(TelegramMiniAppError):
            verify_telegram_webapp_init_data(init_data, bot_token=BOT_TOKEN)

    def test_valid_login_creates_and_reuses_user(self):
        init_data = _build_init_data(user_id=777002)
        result = login_with_telegram_miniapp(init_data, bot_token=BOT_TOKEN)
        self.assertTrue(result["is_new_user"])
        first_user_id = result["user"].id

        # Haqiqiy Mini App har safar ochilganda yangi `auth_date` (demak,
        # yangi `hash`) bilan initData yaratadi — shuning uchun ikkinchi
        # login uchun boshqa `auth_date` beramiz (H-8 nonce himoyasi bitta
        # `hash`ni faqat bir marta qabul qiladi).
        second_init_data = _build_init_data(user_id=777002, auth_date=int(time.time()) + 1)
        second_login = login_with_telegram_miniapp(second_init_data, bot_token=BOT_TOKEN)
        self.assertFalse(second_login["is_new_user"])
        self.assertEqual(second_login["user"].id, first_user_id)


class TelegramLoginCodeSingleUseTests(TestCase):
    """Verifies single_use_telegram_login_challenges: a login code must not
    be redeemable twice, and a code must not be guessable from an unrelated
    session_id."""

    def setUp(self):
        TelegramBotSettings.objects.update_or_create(
            pk=1, defaults={"is_enabled": True, "bot_token": BOT_TOKEN},
        )

    def test_code_cannot_be_redeemed_twice(self):
        session = init_telegram_code_session()
        session_id = session["session_id"]
        code = generate_telegram_code_for_user(
            {"id": 888001, "first_name": "QA", "username": "qa_code_user"},
            session_id=session_id,
        )

        result = verify_telegram_code(code, session_id=session_id)
        self.assertIsNotNone(result["user"])

        from apps.accounts.services.telegram_code_auth import TelegramCodeAuthError
        with self.assertRaises(TelegramCodeAuthError):
            verify_telegram_code(code, session_id=session_id)

    def test_wrong_code_does_not_authenticate(self):
        session = init_telegram_code_session()
        session_id = session["session_id"]
        real_code = generate_telegram_code_for_user(
            {"id": 888002, "first_name": "QA"}, session_id=session_id,
        )
        wrong_code = "11111" if real_code != "11111" else "22222"

        from apps.accounts.services.telegram_code_auth import TelegramCodeAuthError
        with self.assertRaises(TelegramCodeAuthError):
            verify_telegram_code(wrong_code, session_id=session_id)

        # The real code must still work afterwards (one bad guess should not
        # burn the valid code), as long as attempts stay under the limit.
        result = verify_telegram_code(real_code, session_id=session_id)
        self.assertIsNotNone(result["user"])
