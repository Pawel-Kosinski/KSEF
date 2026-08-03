"""Szyfrowanie RSA-OAEP SHA-256 oraz AES-256-CBC dla integracji KSeF."""

import base64
import secrets
from dataclasses import dataclass

from cryptography import x509
from cryptography.hazmat.primitives import hashes, padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.services.ksef.models import PublicKeyCertificate

SYMMETRIC_KEY_LENGTH = 32
IV_LENGTH = 16


@dataclass(frozen=True)
class ExportEncryptionMaterial:
    """Klucz symetryczny + metadane do żądania POST /invoices/exports."""

    symmetric_key: bytes
    iv: bytes
    encrypted_symmetric_key_b64: str
    initialization_vector_b64: str
    public_key_id: str


def build_token_plaintext(ksef_token: str, timestamp_ms: int) -> bytes:
    """Łańcuch {tokenKSeF}|{timestampMs} – zgodnie z dokumentacją uwierzytelniania."""
    return f"{ksef_token}|{timestamp_ms}".encode("utf-8")


def encrypt_bytes_rsa_oaep_sha256(plaintext: bytes, certificate_b64: str) -> bytes:
    """
    Szyfruje dane algorytmem RSA-OAEP z SHA-256 (MGF1).
    Certyfikat w formacie DER zakodowany Base64.
    """
    cert_der = base64.b64decode(certificate_b64)
    cert = x509.load_der_x509_certificate(cert_der)
    public_key = cert.public_key()
    return public_key.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def encrypt_ksef_token_rsa_oaep(plaintext: bytes, certificate_b64: str) -> bytes:
    """Alias zachowany dla kompatybilności z modułem auth."""
    return encrypt_bytes_rsa_oaep_sha256(plaintext, certificate_b64)


def encrypt_ksef_token(
    ksef_token: str,
    timestamp_ms: int,
    certificate: PublicKeyCertificate,
) -> tuple[str, str]:
    """Zwraca (encrypted_token_b64, public_key_id)."""
    plaintext = build_token_plaintext(ksef_token, timestamp_ms)
    encrypted = encrypt_bytes_rsa_oaep_sha256(plaintext, certificate.certificate)
    return base64.b64encode(encrypted).decode("ascii"), certificate.public_key_id


def select_ksef_token_encryption_cert(
    certificates: list[PublicKeyCertificate],
) -> PublicKeyCertificate:
    """Wybiera certyfikat z usage KsefTokenEncryption."""
    for cert in certificates:
        if "KsefTokenEncryption" in cert.usage:
            return cert
    raise ValueError("Brak certyfikatu KsefTokenEncryption w odpowiedzi KSeF")


def select_symmetric_key_encryption_cert(
    certificates: list[PublicKeyCertificate],
) -> PublicKeyCertificate:
    """Wybiera certyfikat z usage SymmetricKeyEncryption (eksport paczek)."""
    for cert in certificates:
        if "SymmetricKeyEncryption" in cert.usage:
            return cert
    raise ValueError("Brak certyfikatu SymmetricKeyEncryption w odpowiedzi KSeF")


def generate_symmetric_key() -> bytes:
    """Losowy klucz AES-256 (32 bajty)."""
    return secrets.token_bytes(SYMMETRIC_KEY_LENGTH)


def generate_initialization_vector() -> bytes:
    """Losowy wektor IV (16 bajtów) dla AES-CBC."""
    return secrets.token_bytes(IV_LENGTH)


def build_export_encryption_material(
    certificates: list[PublicKeyCertificate],
) -> ExportEncryptionMaterial:
    """
    Generuje klucz symetryczny i IV, szyfruje klucz certyfikatem MF.
    Zgodnie z OpenAPI KSeF 2.0 dla POST /invoices/exports.
    """
    cert = select_symmetric_key_encryption_cert(certificates)
    symmetric_key = generate_symmetric_key()
    iv = generate_initialization_vector()
    encrypted_key = encrypt_bytes_rsa_oaep_sha256(symmetric_key, cert.certificate)
    return ExportEncryptionMaterial(
        symmetric_key=symmetric_key,
        iv=iv,
        encrypted_symmetric_key_b64=base64.b64encode(encrypted_key).decode("ascii"),
        initialization_vector_b64=base64.b64encode(iv).decode("ascii"),
        public_key_id=cert.public_key_id,
    )


def decrypt_aes256_cbc_pkcs7(encrypted: bytes, key: bytes, iv: bytes) -> bytes:
    """
    Deszyfruje paczkę ZIP z eksportu KSeF (AES-256-CBC, dopełnienie PKCS#7).

    Operuje wyłącznie na bytes w RAM – bez zapisu na dysk.
    """
    if len(key) != SYMMETRIC_KEY_LENGTH:
        raise ValueError(f"Klucz symetryczny musi mieć {SYMMETRIC_KEY_LENGTH} bajtów")
    if len(iv) != IV_LENGTH:
        raise ValueError(f"IV musi mieć {IV_LENGTH} bajtów")

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(encrypted) + decryptor.finalize()

    unpadder = sym_padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def decrypt_export_package_in_memory(
    encrypted: bytes,
    material: ExportEncryptionMaterial,
) -> bytes:
    """
    Odszyfrowuje zaszyfrowaną część paczki KSeF w pamięci (io.BytesIO downstream).

    Surowe dane KSeF nie są zapisywane na dysku serwera.
    """
    return decrypt_aes256_cbc_pkcs7(
        encrypted,
        material.symmetric_key,
        material.iv,
    )
