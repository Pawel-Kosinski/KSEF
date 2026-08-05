"""Testy szyfrowania tokenów KSeF."""

import pytest

from app.config import get_settings
from app.services.encryption_service import (
    EncryptionError,
    decrypt_ksef_token,
    encrypt_ksef_token,
)


@pytest.fixture(autouse=True)
def encryption_key(monkeypatch):
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_MASTER_KEY", key)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_encrypt_decrypt_roundtrip():
    plain = "token|nip-1186638420|secret"
    encrypted = encrypt_ksef_token(plain)
    assert encrypted != plain
    assert decrypt_ksef_token(encrypted) == plain


def test_encrypt_rejects_empty_token():
    with pytest.raises(EncryptionError, match="pusty"):
        encrypt_ksef_token("   ")
