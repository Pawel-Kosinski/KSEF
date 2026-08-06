"""Reguły kategorii per kontrahent (NIP) – rule engine przed LLM."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ContractorCategoryRule


async def get_contractor_rule(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    contractor_nip: str,
) -> ContractorCategoryRule | None:
    nip = contractor_nip.strip()
    if not nip:
        return None
    result = await session.execute(
        select(ContractorCategoryRule).where(
            ContractorCategoryRule.tenant_id == tenant_id,
            ContractorCategoryRule.contractor_nip == nip,
        )
    )
    return result.scalar_one_or_none()


async def upsert_contractor_rule(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    contractor_nip: str,
    category_main: str,
    *,
    category_sub: str = "Inne",
    contractor_name: str | None = None,
) -> ContractorCategoryRule:
    nip = contractor_nip.strip()
    existing = await get_contractor_rule(session, tenant_id, nip)
    now = datetime.now(timezone.utc)

    if existing is not None:
        existing.category_main = category_main
        existing.category_sub = category_sub
        if contractor_name:
            existing.contractor_name = contractor_name
        existing.updated_at = now
        await session.flush()
        return existing

    rule = ContractorCategoryRule(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        contractor_nip=nip,
        contractor_name=contractor_name,
        category_main=category_main,
        category_sub=category_sub,
        created_at=now,
        updated_at=now,
    )
    session.add(rule)
    await session.flush()
    return rule
