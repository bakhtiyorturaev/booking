import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


ENCRYPTED_PREFIX = "encrypted::"


def _cipher():
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


class EncryptedTextField(models.TextField):
    """Encrypt secrets in the database while exposing plaintext to Python."""

    def _decrypt(self, value):
        if not value or not value.startswith(ENCRYPTED_PREFIX):
            return value
        try:
            encrypted = value.removeprefix(ENCRYPTED_PREFIX).encode()
            return _cipher().decrypt(encrypted).decode()
        except (InvalidToken, ValueError):
            return ""

    def from_db_value(self, value, expression, connection):
        return self._decrypt(value)

    def to_python(self, value):
        return self._decrypt(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        if value.startswith(ENCRYPTED_PREFIX):
            return value
        encrypted = _cipher().encrypt(value.encode()).decode()
        return f"{ENCRYPTED_PREFIX}{encrypted}"

