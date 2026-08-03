"""Asynchroniczny klient HTTP KSeF API 2.0."""

from typing import Any

import httpx

from app.config import Settings, get_settings
from app.services.ksef.exceptions import KsefApiError
from app.services.ksef.models import (
    AuthChallengeResponse,
    AuthInitResponse,
    AuthStatusResponse,
    ExportInitResponse,
    ExportStatusResponse,
    InvoiceExportRequest,
    KsefTokenAuthRequest,
    PublicKeyCertificate,
    TokenRedeemResponse,
)


class KsefClient:
    """
    Klient REST KSeF 2.0 (httpx async).

    Endpointy zgodne z dokumentacją projektu i specyfikacją OpenAPI KSeF:
    - POST /auth/challenge
    - GET  /security/public-key-certificates
    - POST /auth/ksef-token
    - GET  /auth/{referenceNumber}
    - POST /auth/token/redeem
    - POST /invoices/exports
    - GET  /invoices/exports/{referenceNumber}
  """

    def __init__(
        self,
        base_url: str | None = None,
        settings: Settings | None = None,
        timeout: float = 30.0,
    ):
        self._settings = settings or get_settings()
        self._base_url = (base_url or self._settings.ksef_base_url).rstrip("/")
        self._timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        bearer_token: str | None = None,
        expected_status: int | tuple[int, ...] = 200,
    ) -> Any:
        headers: dict[str, str] = {"Accept": "application/json"}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        if json is not None:
            headers["Content-Type"] = "application/json"

        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(method, url, headers=headers, json=json)

        if isinstance(expected_status, int):
            expected = (expected_status,)
        else:
            expected = expected_status

        if response.status_code not in expected:
            detail = response.text
            raise KsefApiError(
                f"KSeF API {method} {path} → HTTP {response.status_code}",
                status_code=response.status_code,
                details=detail,
            )

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def get_auth_challenge(self) -> AuthChallengeResponse:
        """POST /auth/challenge – pobiera challenge i timestampMs."""
        data = await self._request("POST", "/auth/challenge", expected_status=(200, 202))
        return AuthChallengeResponse.model_validate(data)

    async def get_public_key_certificates(self) -> list[PublicKeyCertificate]:
        """GET /security/public-key-certificates."""
        data = await self._request("GET", "/security/public-key-certificates")
        return [PublicKeyCertificate.model_validate(item) for item in data]

    async def submit_ksef_token_auth(
        self, request: KsefTokenAuthRequest
    ) -> AuthInitResponse:
        """POST /auth/ksef-token – rozpoczyna uwierzytelnianie tokenem KSeF."""
        data = await self._request(
            "POST",
            "/auth/ksef-token",
            json=request.model_dump(by_alias=True, exclude_none=True),
            expected_status=(200, 202),
        )
        return AuthInitResponse.model_validate(data)

    async def get_auth_status(
        self, reference_number: str, authentication_token: str
    ) -> AuthStatusResponse:
        """GET /auth/{referenceNumber} – status operacji uwierzytelniania."""
        data = await self._request(
            "GET",
            f"/auth/{reference_number}",
            bearer_token=authentication_token,
        )
        return AuthStatusResponse.model_validate(data)

    async def redeem_tokens(self, authentication_token: str) -> TokenRedeemResponse:
        """POST /auth/token/redeem – pobiera accessToken i refreshToken (jednorazowo)."""
        data = await self._request(
            "POST",
            "/auth/token/redeem",
            bearer_token=authentication_token,
            expected_status=(200, 202),
        )
        return TokenRedeemResponse.model_validate(data)

    async def start_invoice_export(
        self,
        access_token: str,
        request: InvoiceExportRequest,
    ) -> ExportInitResponse:
        """POST /invoices/exports – inicjuje asynchroniczny eksport paczki faktur."""
        data = await self._request(
            "POST",
            "/invoices/exports",
            json=request.model_dump(by_alias=True, exclude_none=True),
            bearer_token=access_token,
            expected_status=(200, 201),
        )
        return ExportInitResponse.model_validate(data)

    async def get_export_status(
        self,
        reference_number: str,
        access_token: str,
    ) -> ExportStatusResponse:
        """GET /invoices/exports/{referenceNumber} – status eksportu."""
        data = await self._request(
            "GET",
            f"/invoices/exports/{reference_number}",
            bearer_token=access_token,
        )
        return ExportStatusResponse.model_validate(data)

    async def download_export_part(self, url: str, method: str = "GET") -> bytes:
        """
        Pobiera zaszyfrowaną część paczki z pre-signed URL.
        Link nie wymaga nagłówka Authorization (OpenAPI KSeF 2.0).
        """
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            response = await client.request(method, url)

        if response.status_code != 200:
            raise KsefApiError(
                f"Pobieranie części paczki → HTTP {response.status_code}",
                status_code=response.status_code,
                details=response.text,
            )
        return response.content
