"""Testy kryptografii eksportu KSeF (AES-256-CBC, klucz symetryczny)."""

import pytest
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.services.ksef.crypto import (
    IV_LENGTH,
    SYMMETRIC_KEY_LENGTH,
    decrypt_aes256_cbc_pkcs7,
    generate_initialization_vector,
    generate_symmetric_key,
)


def _encrypt_aes256_cbc_pkcs7(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    """Pomocnicza funkcja testowa – symuluje szyfrowanie po stronie KSeF."""
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def test_generate_symmetric_key_and_iv_lengths():
    key = generate_symmetric_key()
    iv = generate_initialization_vector()
    assert len(key) == SYMMETRIC_KEY_LENGTH
    assert len(iv) == IV_LENGTH


def test_aes256_cbc_roundtrip():
    key = generate_symmetric_key()
    iv = generate_initialization_vector()
    original = b"PKCS7 padded zip payload test data"
    encrypted = _encrypt_aes256_cbc_pkcs7(original, key, iv)
    decrypted = decrypt_aes256_cbc_pkcs7(encrypted, key, iv)
    assert decrypted == original


def test_decrypt_rejects_invalid_key_length():
    with pytest.raises(ValueError, match="32"):
        decrypt_aes256_cbc_pkcs7(b"data", b"short", b"x" * IV_LENGTH)
