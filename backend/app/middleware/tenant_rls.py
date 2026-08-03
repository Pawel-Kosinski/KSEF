"""
Middleware RLS – alternatywna warstwa do Dependency Injection.

Przechowuje tenant_id w request.state; endpointy mogą go odczytać
i przekazać do get_tenant_db(). Główna ścieżka autoryzacji opiera się
na dependency get_rls_session w app.dependencies.tenant.
"""

from uuid import UUID

from fastapi import Request
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.dependencies.tenant import decode_jwt_token


class TenantRLSMiddleware(BaseHTTPMiddleware):
    """
    Wyodrębnia tenant_id z nagłówka Authorization i zapisuje w request.state.
    Nie wykonuje SET LOCAL – to robi warstwa sesji DB (get_tenant_db).
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.tenant_id = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                payload = decode_jwt_token(token)
                tenant_raw = payload.get("tenant_id")
                if tenant_raw:
                    request.state.tenant_id = UUID(str(tenant_raw))
            except (JWTError, ValueError):
                pass

        return await call_next(request)
