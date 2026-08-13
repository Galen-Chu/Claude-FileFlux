"""
Transparent at-rest encryption for sensitive model fields.

EncryptedTextField encrypts on write (get_prep_value) and decrypts on read
(from_db_value), so existing code that reads/writes the field sees plaintext
while the database stores ciphertext. Legacy plaintext values are passed
through on read so a migration does not break pre-encryption rows.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet() -> Fernet:
    """Return a Fernet instance, using ENCRYPTION_KEY or one derived from SECRET_KEY."""
    key = getattr(settings, 'ENCRYPTION_KEY', '')
    if not key:
        # Derive a 32-byte urlsafe-base64 key from SECRET_KEY for dev convenience.
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(value):
    """Encrypt a string; pass None/empty through unchanged."""
    if value is None or value == '':
        return value
    return _get_fernet().encrypt(value.encode('utf-8')).decode('ascii')


def decrypt_value(value):
    """Decrypt a string; pass None/empty through. Returns plaintext on failure unchanged."""
    if value is None or value == '':
        return value
    try:
        return _get_fernet().decrypt(value.encode('utf-8')).decode('utf-8')
    except (InvalidToken, ValueError):
        # Likely a legacy plaintext value written before encryption was enabled.
        return value


class EncryptedTextField(models.TextField):
    """TextField that transparently encrypts its value at rest."""

    description = "TextField with transparent at-rest encryption"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return encrypt_value(value)

    def from_db_value(self, value, expression, connection):
        return decrypt_value(value)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs
