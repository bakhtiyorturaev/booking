"""M-1: `get_client_ip` ishonchsiz manbadan (hoziyatdagi mijozning o'zidan)
kelgan `X-Forwarded-For` headerini har doim ishonib qabul qilardi — demak
har qanday mijoz bu headerni o'zi yuborib, sessiya/log yozuvlaridagi IP
manzilini soxtalashtirishi mumkin edi. Endi faqat so'rov haqiqatan ham
`settings.TRUSTED_PROXY_IPS` ro'yxatidagi ishonchli teskari-proksidan
kelgan bo'lsagina bu header hisobga olinadi."""
from types import SimpleNamespace

from django.test import TestCase

from apps.accounts.utils import get_client_ip


def _fake_request(remote_addr, forwarded_for=None):
    meta = {"REMOTE_ADDR": remote_addr}
    if forwarded_for is not None:
        meta["HTTP_X_FORWARDED_FOR"] = forwarded_for
    return SimpleNamespace(META=meta)


class ClientIpSpoofingTests(TestCase):
    def test_untrusted_remote_address_ignores_forwarded_header(self):
        request = _fake_request("203.0.113.9", forwarded_for="1.2.3.4")
        self.assertEqual(get_client_ip(request), "203.0.113.9")

    def test_trusted_proxy_forwarded_header_is_honored(self):
        request = _fake_request("127.0.0.1", forwarded_for="1.2.3.4, 5.6.7.8")
        self.assertEqual(get_client_ip(request), "1.2.3.4")

    def test_no_forwarded_header_falls_back_to_remote_addr(self):
        request = _fake_request("127.0.0.1")
        self.assertEqual(get_client_ip(request), "127.0.0.1")

    def test_missing_request_returns_none(self):
        self.assertIsNone(get_client_ip(None))
