"""Serwis listy i szczegółów faktur."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Invoice, InvoiceLine
from app.schemas.invoices import InvoiceDetail, InvoiceLineRead, InvoiceListItem


class InvoiceNotFoundError(Exception):
    """Faktura nie istnieje lub nie należy do tenanta (RLS)."""


class InvoiceService:
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self._session = session
        self._tenant_id = tenant_id

    async def list_invoices(
        self,
        role: str | None = None,
        limit: int = 50,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[InvoiceListItem]:
        capped = max(1, min(limit, 100))
        line_sum_expr = func.sum(InvoiceLine.line_net_value).label("lines_net")
        line_count_expr = func.count(InvoiceLine.id).label("line_count")

        stmt = (
            select(
                Invoice,
                line_sum_expr,
                line_count_expr,
            )
            .join(InvoiceLine, InvoiceLine.invoice_id == Invoice.id)
            .where(Invoice.tenant_id == self._tenant_id)
            .group_by(Invoice.id)
            .order_by(Invoice.issue_date.desc(), Invoice.created_at.desc())
            .limit(capped)
        )
        if role is not None:
            stmt = stmt.where(Invoice.invoice_role == role)
        if date_from is not None:
            stmt = stmt.where(Invoice.issue_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Invoice.issue_date <= date_to)

        rows = (await self._session.execute(stmt)).all()
        return [
            InvoiceListItem(
                id=invoice.id,
                ksef_number=invoice.ksef_number,
                invoice_number=invoice.invoice_number,
                issue_date=invoice.issue_date,
                sale_date=invoice.sale_date,
                seller_nip=invoice.seller_nip,
                buyer_nip=invoice.buyer_nip,
                contractor_name=invoice.contractor_name,
                invoice_role=invoice.invoice_role,
                currency_code=invoice.currency_code,
                total_net=invoice.total_net if invoice.total_net is not None else Decimal(lines_net or 0),
                total_vat=invoice.total_vat,
                total_gross=invoice.total_gross,
                line_count=int(line_count or 0),
            )
            for invoice, lines_net, line_count in rows
        ]

    async def get_invoice(self, invoice_id: UUID) -> InvoiceDetail:
        stmt = (
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.tenant_id == self._tenant_id)
            .options(selectinload(Invoice.lines))
        )
        invoice = (await self._session.execute(stmt)).scalar_one_or_none()
        if invoice is None:
            raise InvoiceNotFoundError(str(invoice_id))

        lines = sorted(invoice.lines, key=lambda line: line.line_number)
        lines_net = sum((line.line_net_value for line in lines), start=Decimal("0"))
        total_net = invoice.total_net if invoice.total_net is not None else lines_net

        return InvoiceDetail(
            id=invoice.id,
            ksef_number=invoice.ksef_number,
            invoice_number=invoice.invoice_number,
            issue_date=invoice.issue_date,
            sale_date=invoice.sale_date,
            seller_nip=invoice.seller_nip,
            buyer_nip=invoice.buyer_nip,
            contractor_name=invoice.contractor_name,
            invoice_role=invoice.invoice_role,
            currency_code=invoice.currency_code,
            total_net=total_net,
            total_vat=invoice.total_vat,
            total_gross=invoice.total_gross,
            lines=[
                InvoiceLineRead(
                    id=line.id,
                    line_number=line.line_number,
                    product_name=line.product_name,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    line_net_value=line.line_net_value,
                    ai_category_main=line.ai_category_main,
                    ai_category_sub=line.ai_category_sub,
                    ai_confidence=line.ai_confidence,
                )
                for line in lines
            ],
        )
