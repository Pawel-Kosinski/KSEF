from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    """Wstrzykuje tenant_id do zmiennej sesyjnej PostgreSQL (SET LOCAL via set_config)."""
    await session.execute(
        text("SELECT set_config('app.current_tenant', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Sesja bazodanowa bez kontekstu tenanta – wyłącznie do operacji systemowych."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
