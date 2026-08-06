"""Aktualizacja kategorii faktury i uczenie reguł kontrahentów."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Invoice, InvoiceLine
from app.services.contractor_rules import upsert_contractor_rule
from app.services.invoice_primary_category import update_invoice_primary_category
from app.services.invoice_roles import resolve_contractor_nip
from app.services.tenant_categories import resolve_tenant_categories


class InvoiceNotFoundError(Exception):
    pass


class InvalidCategoryError(Exception):
    pass


class LineNotFoundError(Exception):
    pass


class InvoiceCategoryService:
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self._session = session
        self._tenant_id = tenant_id

    async def update_invoice_category(
        self,
        invoice_id: UUID,
        category_main: str,
        category_sub: str | None = None,
    ) -> Invoice:
        allowed = await resolve_tenant_categories(self._session, self._tenant_id)
        if category_main not in allowed:
            raise InvalidCategoryError(
                f"Kategoria musi być jedną z: {', '.join(allowed)}"
            )

        sub = (category_sub or "Inne").strip() or "Inne"
        stmt = (
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.tenant_id == self._tenant_id)
        )
        invoice = (await self._session.execute(stmt)).scalar_one_or_none()
        if invoice is None:
            raise InvoiceNotFoundError(str(invoice_id))

        lines_result = await self._session.execute(
            select(InvoiceLine).where(
                InvoiceLine.invoice_id == invoice_id,
                InvoiceLine.tenant_id == self._tenant_id,
            )
        )
        lines = list(lines_result.scalars().all())

        for line in lines:
            line.ai_category_main = category_main
            line.ai_category_sub = sub
            line.ai_confidence = 100
            line.category_source = "user"

        update_invoice_primary_category(invoice, lines)

        contractor_nip = resolve_contractor_nip(
            invoice.invoice_role,
            invoice.seller_nip,
            invoice.buyer_nip,
        )
        await upsert_contractor_rule(
            self._session,
            self._tenant_id,
            contractor_nip,
            category_main,
            category_sub=sub,
            contractor_name=invoice.contractor_name,
        )

        await self._session.flush()
        return invoice

    async def update_line_category(
        self,
        invoice_id: UUID,
        line_id: UUID,
        category_main: str,
        category_sub: str | None = None,
        *,
        learn_rule: bool = False,
    ) -> tuple[InvoiceLine, Invoice]:
        allowed = await resolve_tenant_categories(self._session, self._tenant_id)
        if category_main not in allowed:
            raise InvalidCategoryError(
                f"Kategoria musi być jedną z: {', '.join(allowed)}"
            )

        sub = (category_sub or "Inne").strip() or "Inne"

        invoice = (
            await self._session.execute(
                select(Invoice).where(
                    Invoice.id == invoice_id,
                    Invoice.tenant_id == self._tenant_id,
                )
            )
        ).scalar_one_or_none()
        if invoice is None:
            raise InvoiceNotFoundError(str(invoice_id))

        line = (
            await self._session.execute(
                select(InvoiceLine).where(
                    InvoiceLine.id == line_id,
                    InvoiceLine.invoice_id == invoice_id,
                    InvoiceLine.tenant_id == self._tenant_id,
                )
            )
        ).scalar_one_or_none()
        if line is None:
            raise LineNotFoundError(str(line_id))

        line.ai_category_main = category_main
        line.ai_category_sub = sub
        line.ai_confidence = 100
        line.category_source = "user"

        lines_result = await self._session.execute(
            select(InvoiceLine).where(
                InvoiceLine.invoice_id == invoice_id,
                InvoiceLine.tenant_id == self._tenant_id,
            )
        )
        lines = list(lines_result.scalars().all())
        update_invoice_primary_category(invoice, lines)

        if learn_rule:
            contractor_nip = resolve_contractor_nip(
                invoice.invoice_role,
                invoice.seller_nip,
                invoice.buyer_nip,
            )
            await upsert_contractor_rule(
                self._session,
                self._tenant_id,
                contractor_nip,
                category_main,
                category_sub=sub,
                contractor_name=invoice.contractor_name,
            )

        await self._session.flush()
        return line, invoice
