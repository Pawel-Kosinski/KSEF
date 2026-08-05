"""Szyfrowanie symetryczne tokenów KSeF (Fernet)."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class EncryptionError(Exception):
    """Błąd szyfrowania lub deszyfrowania danych wrażliwych."""


def _get_fernet() -> Fernet:
    key = get_settings().encryption_master_key.strip()
    if not key:
        raise EncryptionError(
            "Brak ENCRYPTION_MASTER_KEY w konfiguracji serwera"
        )
    return Fernet(key.encode("utf-8"))


def encrypt_ksef_token(plain_token: str) -> str:
    """Szyfruje token KSeF przed zapisem w bazie."""
    token = plain_token.strip()
    if not token:
        raise EncryptionError("Token KSeF nie może być pusty")
    return _get_fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_ksef_token(encrypted_token: str) -> str:
    """Deszyfruje token KSeF pobrany z bazy (tylko w pamięci procesu)."""
    try:
        return _get_fernet().decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionError("Nie udało się odszyfrować tokena KSeF") from exc
