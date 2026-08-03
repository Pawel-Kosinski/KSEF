"""Pobieranie kategorii kosztowych tenanta z PostgreSQL (RLS)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import TenantCategory
from app.services.ai.schemas import DEFAULT_TENANT_CATEGORIES


async def fetch_active_category_names(
    session: AsyncSession,
    tenant_id: UUID,
) -> list[str]:
    """
    Zwraca aktywne nazwy kategorii dla tenanta, posortowane wg sort_order.
    Wymaga sesji z ustawionym SET LOCAL app.current_tenant.
    """
    result = await session.execute(
        select(TenantCategory.name)
        .where(
            TenantCategory.tenant_id == tenant_id,
            TenantCategory.is_active.is_(True),
        )
        .order_by(TenantCategory.sort_order, TenantCategory.name)
    )
    return list(result.scalars().all())


async def resolve_tenant_categories(
    session: AsyncSession,
    tenant_id: UUID,
) -> list[str]:
    """Kategorie z bazy lub domyślny zestaw MVP, gdy tenant nie ma własnych."""
    names = await fetch_active_category_names(session, tenant_id)
    if names:
        return names
    return list(DEFAULT_TENANT_CATEGORIES)
