from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.session import get_tenant_db

security = HTTPBearer(auto_error=False)
settings = get_settings()


class TenantContext:
    """Kontekst dzierżawcy wyekstrahowany z tokena JWT."""

    def __init__(self, tenant_id: UUID, sub: str | None = None):
        self.tenant_id = tenant_id
        self.sub = sub


def decode_jwt_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TenantContext:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak tokena autoryzacyjnego",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_jwt_token(credentials.credentials)
        tenant_id_raw = payload.get("tenant_id")
        if tenant_id_raw is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token JWT nie zawiera tenant_id",
            )
        tenant_id = UUID(str(tenant_id_raw))
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy token JWT",
        ) from exc

    return TenantContext(tenant_id=tenant_id, sub=payload.get("sub"))


async def get_rls_session(
    tenant: TenantContext = Depends(get_current_tenant),
) -> AsyncGenerator[AsyncSession, None]:
    """Dependency Injection: sesja DB z aktywnym RLS dla bieżącego tenanta."""
    async for session in get_tenant_db(tenant.tenant_id):
        yield session
