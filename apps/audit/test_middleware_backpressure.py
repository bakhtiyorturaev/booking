"""`_audit_executor` (apps/audit/middleware.py) ichki navbati standart
holatda cheksiz — DB sekinlashganda yoki trafik keskin oshganda `.submit()`
xotirada cheksiz to'planib ketishi mumkin edi. Endi bir vaqtning o'zida
navbatda/bajarilishda turadigan vazifalar soni chegaralangan; undan oshsa
yozuv sinxron bajariladi (ma'lumot yo'qolmaydi)."""
from django.test import TestCase

from apps.audit.middleware import _audit_queue_capacity, _submit_audit_log
from apps.audit.models import AuditLog


def _log_kwargs(**overrides):
    base = dict(
        actor_id=None,
        method="POST",
        path="/api/v1/qa/",
        action="qa.action",
        object_id="",
        status_code=200,
        ip_address="127.0.0.1",
        user_agent="pytest",
        request_id="qa-request",
    )
    base.update(overrides)
    return base


class AuditBackpressureTests(TestCase):
    def test_falls_back_to_synchronous_write_when_queue_is_saturated(self):
        acquired = []
        try:
            while _audit_queue_capacity.acquire(blocking=False):
                acquired.append(True)

            _submit_audit_log(**_log_kwargs(path="/api/v1/qa/saturated/"))

            self.assertTrue(
                AuditLog.objects.filter(path="/api/v1/qa/saturated/").exists(),
                "Navbat to'lib ketganda ham audit yozuvi sinxron saqlanishi kerak",
            )
        finally:
            for _ in acquired:
                _audit_queue_capacity.release()

    def test_submits_asynchronously_when_capacity_is_available(self):
        from unittest.mock import patch

        import apps.audit.middleware as middleware_module

        with patch.object(middleware_module._audit_executor, "submit") as submit:
            _submit_audit_log(**_log_kwargs(path="/api/v1/qa/async/"))
            submit.assert_called_once()

        # `.submit()` mocklangani uchun ishchi vazifa hech qachon bajarilmadi —
        # shuning uchun navbat sig'imi hali ham egallangan holda qoladi;
        # keyingi testlarga ta'sir qilmasligi uchun qo'lda bo'shatamiz.
        middleware_module._audit_queue_capacity.release()
        self.assertFalse(
            AuditLog.objects.filter(path="/api/v1/qa/async/").exists(),
            "Sig'im bo'sh bo'lsa, yozuv darhol emas, executor orqali ketishi kerak",
        )
