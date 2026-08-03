"""Agregacje statystyczne po stronie PostgreSQL (SQLAlchemy)."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Invoice, InvoiceLine
from app.schemas.stats import (
    CostStructureItem,
    CostStructureResponse,
    SummaryResponse,
    TopCounterpartyItem,
    TopCounterpartiesResponse,
    TrendItem,
    TrendResponse,
)

UNCATEGORIZED_LABEL = "Niesklasyfikowane"


def resolve_trend_granularity(date_from: date | None, date_to: date | None) -> str:
    if date_from is None or date_to is None:
        return "month"
    span_days = (date_to - date_from).days
    if span_days <= 30:
        return "day"
    if span_days <= 90:
        return "week"
    return "month"


class StatisticsService:
    """Serwis analityki – agregacje na invoice_lines ⨝ invoices."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self._session = session
        self._tenant_id = tenant_id

    def _apply_date_filters(self, stmt, date_from: date | None, date_to: date | None):
        if date_from is not None:
            stmt = stmt.where(Invoice.issue_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Invoice.issue_date <= date_to)
        return stmt

    async def get_summary(
        self,
        role: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> SummaryResponse:
        line_stmt = (
            select(func.coalesce(func.sum(InvoiceLine.line_net_value), Decimal("0")))
            .select_from(InvoiceLine)
            .join(Invoice, InvoiceLine.invoice_id == Invoice.id)
            .where(InvoiceLine.tenant_id == self._tenant_id)
            .where(Invoice.invoice_role == role)
        )
        line_stmt = self._apply_date_filters(line_stmt, date_from, date_to)
        total_net = Decimal((await self._session.execute(line_stmt)).scalar_one())

        invoice_stmt = (
            select(
                func.coalesce(func.sum(Invoice.total_vat), Decimal("0")).label("total_vat"),
                func.coalesce(func.sum(Invoice.total_gross), Decimal("0")).label("total_gross"),
            )
            .select_from(Invoice)
            .where(Invoice.tenant_id == self._tenant_id)
            .where(Invoice.invoice_role == role)
        )
        invoice_stmt = self._apply_date_filters(invoice_stmt, date_from, date_to)
        totals = (await self._session.execute(invoice_stmt)).one()

        return SummaryResponse(
            total_net=total_net,
            total_vat=Decimal(totals.total_vat),
            total_gross=Decimal(totals.total_gross),
            date_from=date_from,
            date_to=date_to,
            role=role,
        )

    async def get_structure(
        self,
        role: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> CostStructureResponse:
        group_expr = func.coalesce(
            InvoiceLine.ai_category_main,
            UNCATEGORIZED_LABEL,
        ).label("category")

        stmt = (
            select(
                group_expr,
                func.sum(InvoiceLine.line_net_value).label("total_net"),
            )
            .select_from(InvoiceLine)
            .join(Invoice, InvoiceLine.invoice_id == Invoice.id)
            .where(InvoiceLine.tenant_id == self._tenant_id)
            .where(Invoice.invoice_role == role)
            .group_by(group_expr)
            .order_by(func.sum(InvoiceLine.line_net_value).desc())
        )
        stmt = self._apply_date_filters(stmt, date_from, date_to)

        result = await self._session.execute(stmt)
        rows = result.all()

        items = [
            CostStructureItem(category=row.category, total_net=Decimal(row.total_net))
            for row in rows
        ]
        total = sum((item.total_net for item in items), start=Decimal("0"))

        return CostStructureResponse(
            items=items,
            total_net=total,
            date_from=date_from,
            date_to=date_to,
            role=role,
        )

    async def get_trend(
        self,
        role: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> TrendResponse:
        granularity = resolve_trend_granularity(date_from, date_to)

        if granularity == "day":
            bucket = Invoice.issue_date
            period_label = func.to_char(Invoice.issue_date, "YYYY-MM-DD").label("period")
            order_expr = Invoice.issue_date
        elif granularity == "week":
            bucket = func.date_trunc("week", Invoice.issue_date)
            period_label = func.to_char(bucket, 'IYYY-"W"IW').label("period")
            order_expr = bucket
        else:
            bucket = func.date_trunc("month", Invoice.issue_date)
            period_label = func.to_char(bucket, "YYYY-MM").label("period")
            order_expr = bucket

        stmt = (
            select(
                period_label,
                func.sum(InvoiceLine.line_net_value).label("total_net"),
            )
            .select_from(InvoiceLine)
            .join(Invoice, InvoiceLine.invoice_id == Invoice.id)
            .where(InvoiceLine.tenant_id == self._tenant_id)
            .where(Invoice.invoice_role == role)
            .group_by(bucket, period_label)
            .order_by(order_expr.asc())
        )
        stmt = self._apply_date_filters(stmt, date_from, date_to)

        result = await self._session.execute(stmt)
        rows = result.all()

        items = [
            TrendItem(period=row.period, total_net=Decimal(row.total_net)) for row in rows
        ]
        total = sum((item.total_net for item in items), start=Decimal("0"))

        return TrendResponse(
            items=items,
            total_net=total,
            granularity=granularity,
            date_from=date_from,
            date_to=date_to,
            role=role,
        )

    async def get_top_counterparties(
        self,
        role: str,
        limit: int = 10,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> TopCounterpartiesResponse:
        capped_limit = max(1, min(limit, 10))
        counterparty_col = Invoice.buyer_nip if role == "sales" else Invoice.seller_nip

        stmt = (
            select(
                counterparty_col.label("counterparty_nip"),
                func.max(Invoice.contractor_name).label("contractor_name"),
                func.max(Invoice.ksef_number).label("ksef_number"),
                func.sum(InvoiceLine.line_net_value).label("total_net"),
            )
            .select_from(InvoiceLine)
            .join(Invoice, InvoiceLine.invoice_id == Invoice.id)
            .where(InvoiceLine.tenant_id == self._tenant_id)
            .where(Invoice.invoice_role == role)
            .group_by(counterparty_col)
            .order_by(func.sum(InvoiceLine.line_net_value).desc())
            .limit(capped_limit)
        )
        stmt = self._apply_date_filters(stmt, date_from, date_to)

        result = await self._session.execute(stmt)
        rows = result.all()

        items = [
            TopCounterpartyItem(
                counterparty_nip=row.counterparty_nip,
                contractor_name=row.contractor_name,
                ksef_number=row.ksef_number,
                total_net=Decimal(row.total_net),
                rank=index,
            )
            for index, row in enumerate(rows, start=1)
        ]

        return TopCounterpartiesResponse(
            items=items,
            limit=capped_limit,
            date_from=date_from,
            date_to=date_to,
            role=role,
        )
