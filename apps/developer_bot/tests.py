import logging
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import connection
from django.test import SimpleTestCase, TestCase

from apps.developer_bot.formatters import (
    TELEGRAM_MESSAGE_LIMIT,
    format_event,
    format_log_record,
    redact_sensitive_data,
)
from apps.developer_bot.logging import TelegramErrorHandler
from apps.developer_bot.models import DeveloperBotSettings
from apps.developer_bot.services import (
    clear_developer_bot_settings_cache,
    developer_bot_is_configured,
    get_developer_bot_client,
)


class DeveloperBotFormatterTests(SimpleTestCase):
    def test_log_record_contains_context_and_redacts_secrets(self):
        record = logging.LogRecord(
            name="django.request",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Request failed password=secret Authorization: Bearer abc.def",
            args=(),
            exc_info=None,
        )

        message = format_log_record(record, environment="test")

        self.assertIn("django.request", message)
        self.assertIn("test", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("abc.def", message)
        self.assertIn("[REDACTED]", message)

    def test_long_message_respects_telegram_limit(self):
        message = format_event("Long event", "x" * 5000)

        self.assertLessEqual(len(message), TELEGRAM_MESSAGE_LIMIT)

    def test_redacts_otp_and_tokens(self):
        value = redact_sensitive_data(
            "otp=1234 access_token=token-value bearer jwt-value"
        )

        self.assertNotIn("1234", value)
        self.assertNotIn("token-value", value)
        self.assertNotIn("jwt-value", value)


class DeveloperBotConfigurationTests(TestCase):
    def tearDown(self):
        clear_developer_bot_settings_cache()

    def test_configuration_requires_enabled_token_and_chat(self):
        configuration, _ = DeveloperBotSettings.objects.update_or_create(
            pk=1,
            defaults={
                "is_enabled": True,
                "bot_token": "token",
                "chat_id": -1001,
            },
        )

        self.assertTrue(developer_bot_is_configured(configuration))

    def test_disabled_configuration_is_not_active(self):
        configuration, _ = DeveloperBotSettings.objects.update_or_create(
            pk=1,
            defaults={
                "is_enabled": False,
                "bot_token": "token",
                "chat_id": -1001,
            },
        )

        self.assertFalse(developer_bot_is_configured(configuration))

    def test_token_is_encrypted_in_database(self):
        DeveloperBotSettings.objects.update_or_create(
            pk=1,
            defaults={"bot_token": "plain-token"},
        )

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT bot_token FROM developer_bot_settings WHERE id = 1"
            )
            stored_token = cursor.fetchone()[0]

        self.assertNotEqual(stored_token, "plain-token")
        self.assertTrue(stored_token.startswith("encrypted::"))

    def test_client_uses_database_configuration(self):
        DeveloperBotSettings.objects.update_or_create(
            pk=1,
            defaults={
                "is_enabled": True,
                "bot_token": "database-token",
                "chat_id": -1001,
                "request_timeout_seconds": 7,
            },
        )
        clear_developer_bot_settings_cache()

        client = get_developer_bot_client()

        self.assertEqual(client.chat_id, -1001)
        self.assertEqual(client.timeout, 7)
        self.assertIn("database-token", client.base_url)


class TelegramErrorHandlerTests(SimpleTestCase):
    @patch("apps.developer_bot.services.get_developer_bot_settings")
    @patch("apps.developer_bot.services.get_developer_bot_client")
    def test_error_record_is_sent(self, get_client, get_configuration):
        client = Mock()
        get_client.return_value = client
        get_configuration.return_value = SimpleNamespace(
            is_configured=True,
            notify_errors=True,
            environment="test",
        )
        handler = TelegramErrorHandler(level=logging.ERROR)
        record = logging.LogRecord(
            name="club_booking",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Unexpected failure",
            args=(),
            exc_info=None,
        )

        handler.handle(record)

        client.send_message.assert_called_once()
        self.assertIn("Unexpected failure", client.send_message.call_args.args[0])
