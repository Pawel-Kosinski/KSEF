"""Serwis uwierzytelniania KSeF 2.0 tokenem systemowym."""

import asyncio

from app.config import Settings, get_settings
from app.services.ksef.client import KsefClient
from app.services.ksef.crypto import encrypt_ksef_token, select_ksef_token_encryption_cert
from app.services.ksef.exceptions import KsefAuthError, KsefAuthTimeoutError
from app.services.ksef.models import (
    ContextIdentifier,
    KsefAccessTokens,
    KsefTokenAuthRequest,
)

AUTH_STATUS_IN_PROGRESS = 100
AUTH_STATUS_SUCCESS = 200


class KsefAuthService:
    """
    Pełny przepływ uwierzytelniania zgodny z dokumentacją projektu:

    1. POST /auth/challenge
    2. Szyfrowanie token|timestampMs (RSA-OAEP SHA-256)
    3. POST /auth/ksef-token
    4. Polling GET /auth/{referenceNumber} (kod 200 = sukces)
    5. POST /auth/token/redeem → accessToken + refreshToken
    """

    def __init__(
        self,
        client: KsefClient | None = None,
        settings: Settings | None = None,
    ):
        self._settings = settings or get_settings()
        self._client = client or KsefClient(settings=self._settings)

    async def authenticate_with_ksef_token(
        self,
        ksef_token: str | None = None,
        nip: str | None = None,
    ) -> KsefAccessTokens:
        token = ksef_token or self._settings.ksef_token
        context_nip = nip or self._settings.ksef_nip

        if not token:
            raise KsefAuthError("Brak tokena KSeF (KSEF_TOKEN)")
        if not context_nip:
            raise KsefAuthError("Brak NIP kontekstu (KSEF_NIP)")

        challenge = await self._client.get_auth_challenge()
        certificates = await self._client.get_public_key_certificates()
        encryption_cert = select_ksef_token_encryption_cert(certificates)

        encrypted_b64, public_key_id = encrypt_ksef_token(
            token,
            challenge.timestamp_ms,
            encryption_cert,
        )

        auth_request = KsefTokenAuthRequest(
            challenge=challenge.challenge,
            context_identifier=ContextIdentifier(type="Nip", value=context_nip),
            encrypted_token=encrypted_b64,
            public_key_id=public_key_id,
        )

        init_response = await self._client.submit_ksef_token_auth(auth_request)
        auth_token = init_response.authentication_token.token
        reference = init_response.reference_number

        await self._wait_for_auth_success(reference, auth_token)

        tokens = await self._client.redeem_tokens(auth_token)
        return KsefAccessTokens(
            access_token=tokens.access_token.token,
            refresh_token=tokens.refresh_token.token,
            access_token_valid_until=tokens.access_token.valid_until,
            refresh_token_valid_until=tokens.refresh_token.valid_until,
            reference_number=reference,
        )

    async def _wait_for_auth_success(
        self, reference_number: str, authentication_token: str
    ) -> None:
        interval = self._settings.ksef_auth_poll_interval_sec
        max_attempts = self._settings.ksef_auth_poll_max_attempts

        for attempt in range(1, max_attempts + 1):
            status = await self._client.get_auth_status(
                reference_number, authentication_token
            )
            code = status.status.code

            if code == AUTH_STATUS_SUCCESS:
                return
            if code != AUTH_STATUS_IN_PROGRESS:
                raise KsefAuthError(
                    f"Uwierzytelnianie nieudane: [{code}] {status.status.description}"
                )

            if attempt < max_attempts:
                await asyncio.sleep(interval)

        raise KsefAuthTimeoutError(
            f"Przekroczono czas oczekiwania na uwierzytelnienie ({max_attempts} prób)"
        )
