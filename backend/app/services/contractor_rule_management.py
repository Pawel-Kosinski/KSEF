"""CRUD reguł kategorii kontrahentów (NIP)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ContractorCategoryRule, Invoice, InvoiceLine
from app.services.tenant_categories import resolve_tenant_categories


class ContractorRuleNotFoundError(Exception):
    pass


class ContractorRuleDuplicateError(Exception):
    pass


class ContractorRuleInvalidCategoryError(Exception):
    pass


class ContractorRuleManagementService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self._session = session
        self._tenant_id = tenant_id

    async def _count_line_usage(self, contractor_nip: str) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(InvoiceLine)
            .join(Invoice, InvoiceLine.invoice_id == Invoice.id)
            .where(
                InvoiceLine.tenant_id == self._tenant_id,
                or_(
                    and_(
                        Invoice.invoice_role == "cost",
                        Invoice.seller_nip == contractor_nip,
                    ),
                    and_(
                        Invoice.invoice_role == "sales",
                        Invoice.buyer_nip == contractor_nip,
                    ),
                ),
            )
        )
        return int(result.scalar_one())

    async def list_rules(self) -> list[dict]:
        result = await self._session.execute(
            select(ContractorCategoryRule)
            .where(ContractorCategoryRule.tenant_id == self._tenant_id)
            .order_by(ContractorCategoryRule.contractor_nip.asc())
        )
        rules = result.scalars().all()
        items: list[dict] = []
        for rule in rules:
            items.append(
                {
                    "id": rule.id,
                    "contractor_nip": rule.contractor_nip,
                    "contractor_name": rule.contractor_name,
                    "category_main": rule.category_main,
                    "category_sub": rule.category_sub,
                    "line_usage_count": await self._count_line_usage(rule.contractor_nip),
                    "updated_at": rule.updated_at,
                }
            )
        return items

    async def create_rule(
        self,
        contractor_nip: str,
        category_main: str,
        *,
        category_sub: str = "Inne",
        contractor_name: str | None = None,
    ) -> dict:
        nip = contractor_nip.strip()
        if not nip:
            raise ValueError("NIP kontrahenta jest wymagany")

        main = category_main.strip()
        allowed = await resolve_tenant_categories(self._session, self._tenant_id)
        if main not in allowed:
            raise ContractorRuleInvalidCategoryError(
                f"Kategoria musi być jedną z: {', '.join(allowed)}"
            )

        existing = await self._session.execute(
            select(ContractorCategoryRule).where(
                ContractorCategoryRule.tenant_id == self._tenant_id,
                ContractorCategoryRule.contractor_nip == nip,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ContractorRuleDuplicateError(nip)

        now = datetime.now(timezone.utc)
        rule = ContractorCategoryRule(
            id=uuid.uuid4(),
            tenant_id=self._tenant_id,
            contractor_nip=nip,
            contractor_name=contractor_name,
            category_main=main,
            category_sub=(category_sub or "Inne").strip() or "Inne",
            created_at=now,
            updated_at=now,
        )
        self._session.add(rule)
        await self._session.flush()
        return {
            "id": rule.id,
            "contractor_nip": rule.contractor_nip,
            "contractor_name": rule.contractor_name,
            "category_main": rule.category_main,
            "category_sub": rule.category_sub,
            "line_usage_count": await self._count_line_usage(rule.contractor_nip),
            "updated_at": rule.updated_at,
        }

    async def delete_rule(self, rule_id: uuid.UUID) -> None:
        result = await self._session.execute(
            delete(ContractorCategoryRule).where(
                ContractorCategoryRule.id == rule_id,
                ContractorCategoryRule.tenant_id == self._tenant_id,
            )
        )
        if result.rowcount == 0:
            raise ContractorRuleNotFoundError(str(rule_id))
