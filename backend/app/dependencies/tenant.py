from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.database.session import async_session_factory, get_db, set_tenant_context
from app.services.auth_service import decode_access_token

security = HTTPBearer(auto_error=False)


class TenantContext:
    """Kontekst dzierżawcy wyekstrahowany z tokena JWT."""

    def __init__(self, tenant_id: UUID, user_id: UUID, email: str | None = None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.email = email
        self.sub = str(user_id)


async def _decode_credentials(
    credentials: HTTPAuthorizationCredentials | None,
) -> TenantContext:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak tokena autoryzacyjnego",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        tenant_id_raw = payload.get("tenant_id")
        user_id_raw = payload.get("sub")
        if tenant_id_raw is None or user_id_raw is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token JWT nie zawiera tenant_id lub sub",
            )
        tenant_id = UUID(str(tenant_id_raw))
        user_id = UUID(str(user_id_raw))
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy token JWT",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        email=payload.get("email"),
    )


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TenantContext:
    return await _decode_credentials(credentials)


async def get_current_user(
    tenant_ctx: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> User:
    result = await session.execute(
        select(User).where(User.id == tenant_ctx.user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Użytkownik nie istnieje lub jest nieaktywny",
        )
    if user.tenant_id != tenant_ctx.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token nie pasuje do konta użytkownika",
        )
    return user


async def require_admin_user(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wymagane uprawnienia administratora",
        )
    return user


async def get_rls_session(
    tenant: TenantContext = Depends(get_current_tenant),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Sesja DB z RLS – kontekst tenanta ustawiany w transakcji (bezpieczne przy poolingu).

    SET LOCAL via set_config(..., true) jest widoczny tylko w bieżącej transakcji
    i jest resetowany po COMMIT/ROLLBACK. Przy błędzie wykonujemy rollback.
    """
    async with async_session_factory() as session:
        try:
            await session.begin()
            await set_tenant_context(session, tenant.tenant_id)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
