"""CRUD kategorii tenanta + seedowanie przy onboardingu."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ContractorCategoryRule, Invoice, InvoiceLine, TenantCategory


class CategoryNotFoundError(Exception):
    pass


class CategoryDuplicateError(Exception):
    pass


class CategoryInUseError(Exception):
    def __init__(self, usage_count: int):
        self.usage_count = usage_count
        super().__init__(f"Kategoria jest używana na {usage_count} fakturach/pozycjach")


async def seed_tenant_categories(
    session: AsyncSession,
    tenant_id: UUID,
    category_names: list[str],
) -> list[TenantCategory]:
    """Tworzy aktywne kategorie tenanta (np. po rejestracji)."""
    created: list[TenantCategory] = []
    for index, name in enumerate(category_names, start=1):
        cleaned = name.strip()
        if not cleaned:
            continue
        row = TenantCategory(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=cleaned[:128],
            sort_order=index,
            is_active=True,
        )
        session.add(row)
        created.append(row)
    await session.flush()
    return created


async def _count_category_usage(
    session: AsyncSession,
    tenant_id: UUID,
    category_name: str,
) -> int:
    line_count = (
        await session.execute(
            select(func.count())
            .select_from(InvoiceLine)
            .where(
                InvoiceLine.tenant_id == tenant_id,
                InvoiceLine.ai_category_main == category_name,
            )
        )
    ).scalar_one()

    invoice_count = (
        await session.execute(
            select(func.count())
            .select_from(Invoice)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.primary_category_main == category_name,
            )
        )
    ).scalar_one()

    rule_count = (
        await session.execute(
            select(func.count())
            .select_from(ContractorCategoryRule)
            .where(
                ContractorCategoryRule.tenant_id == tenant_id,
                ContractorCategoryRule.category_main == category_name,
            )
        )
    ).scalar_one()

    return int(line_count or 0) + int(invoice_count or 0) + int(rule_count or 0)


class TenantCategoryManagementService:
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self._session = session
        self._tenant_id = tenant_id

    async def list_categories(self) -> list[dict]:
        rows = (
            await self._session.execute(
                select(TenantCategory)
                .where(
                    TenantCategory.tenant_id == self._tenant_id,
                    TenantCategory.is_active.is_(True),
                )
                .order_by(TenantCategory.sort_order, TenantCategory.name)
            )
        ).scalars().all()

        items: list[dict] = []
        for row in rows:
            usage = await _count_category_usage(self._session, self._tenant_id, row.name)
            items.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "sort_order": row.sort_order,
                    "invoice_usage_count": usage,
                }
            )
        return items

    async def create_category(self, name: str) -> dict:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Nazwa kategorii nie może być pusta")

        existing = await self._session.execute(
            select(TenantCategory).where(
                TenantCategory.tenant_id == self._tenant_id,
                TenantCategory.is_active.is_(True),
                func.lower(TenantCategory.name) == cleaned.lower(),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise CategoryDuplicateError(cleaned)

        max_order = (
            await self._session.execute(
                select(func.coalesce(func.max(TenantCategory.sort_order), 0)).where(
                    TenantCategory.tenant_id == self._tenant_id
                )
            )
        ).scalar_one()

        row = TenantCategory(
            id=uuid.uuid4(),
            tenant_id=self._tenant_id,
            name=cleaned[:128],
            sort_order=int(max_order or 0) + 1,
            is_active=True,
        )
        self._session.add(row)
        await self._session.flush()
        return {
            "id": row.id,
            "name": row.name,
            "sort_order": row.sort_order,
            "invoice_usage_count": 0,
        }

    async def update_category(self, category_id: UUID, name: str) -> dict:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Nazwa kategorii nie może być pusta")

        row = (
            await self._session.execute(
                select(TenantCategory).where(
                    TenantCategory.id == category_id,
                    TenantCategory.tenant_id == self._tenant_id,
                    TenantCategory.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise CategoryNotFoundError(str(category_id))

        duplicate = await self._session.execute(
            select(TenantCategory).where(
                TenantCategory.tenant_id == self._tenant_id,
                TenantCategory.is_active.is_(True),
                TenantCategory.id != category_id,
                func.lower(TenantCategory.name) == cleaned.lower(),
            )
        )
        if duplicate.scalar_one_or_none() is not None:
            raise CategoryDuplicateError(cleaned)

        old_name = row.name
        row.name = cleaned[:128]
        await self._rename_category_references(old_name, cleaned[:128])
        await self._session.flush()

        usage = await _count_category_usage(self._session, self._tenant_id, row.name)
        return {
            "id": row.id,
            "name": row.name,
            "sort_order": row.sort_order,
            "invoice_usage_count": usage,
        }

    async def delete_category(self, category_id: UUID) -> None:
        row = (
            await self._session.execute(
                select(TenantCategory).where(
                    TenantCategory.id == category_id,
                    TenantCategory.tenant_id == self._tenant_id,
                    TenantCategory.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise CategoryNotFoundError(str(category_id))

        usage = await _count_category_usage(self._session, self._tenant_id, row.name)
        if usage > 0:
            raise CategoryInUseError(usage)

        row.is_active = False
        await self._session.flush()

    async def _rename_category_references(self, old_name: str, new_name: str) -> None:
        lines = (
            await self._session.execute(
                select(InvoiceLine).where(
                    InvoiceLine.tenant_id == self._tenant_id,
                    InvoiceLine.ai_category_main == old_name,
                )
            )
        ).scalars().all()
        for line in lines:
            line.ai_category_main = new_name

        invoices = (
            await self._session.execute(
                select(Invoice).where(
                    Invoice.tenant_id == self._tenant_id,
                    Invoice.primary_category_main == old_name,
                )
            )
        ).scalars().all()
        for invoice in invoices:
            invoice.primary_category_main = new_name

        rules = (
            await self._session.execute(
                select(ContractorCategoryRule).where(
                    ContractorCategoryRule.tenant_id == self._tenant_id,
                    ContractorCategoryRule.category_main == old_name,
                )
            )
        ).scalars().all()
        for rule in rules:
            rule.category_main = new_name
