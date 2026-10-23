"""`_notification_executor` (apps/core/developer_bot/services.py) ichki
navbati standart holatda cheksiz — bronlar "to'lqini" paytida xotirada
cheksiz o'sishi mumkin edi. Endi navbat sig'imi chegaralangan; to'lib
ketganda yangi (faqat monitoring maqsadidagi) bildirishnoma jim tashlab
yuboriladi."""
from unittest.mock import patch

from django.test import TestCase

from apps.core.developer_bot.services import (
    _notification_queue_capacity,
    notify_developer_async,
)
from apps.core.models import DeveloperBotSettings


class DeveloperBotBackpressureTests(TestCase):
    def setUp(self):
        DeveloperBotSettings.objects.update_or_create(
            pk=1,
            defaults={
                "is_enabled": True,
                "bot_token": "123456:QA-TOKEN",
                "chat_id": 42,
                "environment": "test",
            },
        )
        from apps.core.developer_bot import services as bot_services
        bot_services.clear_developer_bot_settings_cache()

    def test_drops_notification_when_queue_is_saturated(self):
        import apps.core.developer_bot.services as services_module

        acquired = []
        try:
            while _notification_queue_capacity.acquire(blocking=False):
                acquired.append(True)

            with patch.object(services_module._notification_executor, "submit") as submit:
                notify_developer_async("QA sarlavha", "QA xabar")
                submit.assert_not_called()
        finally:
            for _ in acquired:
                _notification_queue_capacity.release()

    def test_submits_when_capacity_is_available(self):
        import apps.core.developer_bot.services as services_module

        with patch.object(services_module._notification_executor, "submit") as submit:
            notify_developer_async("QA sarlavha", "QA xabar")
            submit.assert_called_once()

        _notification_queue_capacity.release()
