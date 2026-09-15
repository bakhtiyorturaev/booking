from types import SimpleNamespace

from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from apps.accounts.models import User
from apps.audit.middleware import AuditMiddleware
from apps.audit.models import AuditLog


class AuditMiddlewareTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="audit_user",
            phone="+998901110003",
        )

    @override_settings(TRUSTED_PROXY_IPS={"127.0.0.1"})
    def test_mutating_api_request_is_recorded(self):
        request = RequestFactory().patch(
            "/api/v1/profile/",
            HTTP_X_FORWARDED_FOR="203.0.113.5",
            HTTP_X_REQUEST_ID="request-123",
        )
        request.user = self.user
        request.resolver_match = SimpleNamespace(
            view_name="current-user",
            kwargs={},
        )
        middleware = AuditMiddleware(lambda request: HttpResponse(status=200))

        middleware(request)

        entry = AuditLog.objects.get()
        self.assertEqual(entry.actor, self.user)
        self.assertEqual(entry.method, "PATCH")
        self.assertEqual(entry.ip_address, "203.0.113.5")
        self.assertEqual(entry.request_id, "request-123")

    def test_read_request_is_not_recorded(self):
        request = RequestFactory().get("/api/v1/clubs/")
        request.user = self.user

        AuditMiddleware(lambda request: HttpResponse(status=200))(request)

        self.assertFalse(AuditLog.objects.exists())
