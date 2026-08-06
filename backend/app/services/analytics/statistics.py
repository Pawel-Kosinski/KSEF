"""Agregacje statystyczne po stronie PostgreSQL (SQLAlchemy)."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Invoice, InvoiceLine
from app.schemas.stats import (
    CashflowItem,
    CashflowResponse,
    CostStructureItem,
    CostStructureResponse,
    DashboardResponse,
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

    def _apply_category_filter(self, stmt, category: str | None):
        if category is None:
            return stmt
        if category == UNCATEGORIZED_LABEL:
            return stmt.where(InvoiceLine.ai_category_main.is_(None))
        return stmt.where(InvoiceLine.ai_category_main == category)

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

        invoice_ids_subq = (
            select(Invoice.id)
            .join(InvoiceLine, InvoiceLine.invoice_id == Invoice.id)
            .where(InvoiceLine.tenant_id == self._tenant_id)
            .where(Invoice.invoice_role == role)
        )
        invoice_ids_subq = self._apply_date_filters(invoice_ids_subq, date_from, date_to).distinct()

        invoice_stmt = (
            select(
                func.coalesce(func.sum(Invoice.total_vat), Decimal("0")).label("total_vat"),
                func.coalesce(func.sum(Invoice.total_gross), Decimal("0")).label("total_gross"),
            )
            .select_from(Invoice)
            .where(Invoice.tenant_id == self._tenant_id)
            .where(Invoice.id.in_(invoice_ids_subq))
        )
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
        category: str | None = None,
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
        stmt = self._apply_category_filter(stmt, category)

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
            category=category,
        )

    async def get_cashflow(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> CashflowResponse:
        granularity = resolve_trend_granularity(date_from, date_to)

        if granularity == "day":
            bucket = Invoice.issue_date
            period_label = func.to_char(Invoice.issue_date, "YYYY-MM-DD").label("date")
            order_expr = Invoice.issue_date
        elif granularity == "week":
            bucket = func.date_trunc("week", Invoice.issue_date)
            period_label = func.to_char(bucket, 'IYYY-"W"IW').label("date")
            order_expr = bucket
        else:
            bucket = func.date_trunc("month", Invoice.issue_date)
            period_label = func.to_char(bucket, "YYYY-MM").label("date")
            order_expr = bucket

        sales_expr = func.coalesce(
            func.sum(
                case(
                    (Invoice.invoice_role == "sales", InvoiceLine.line_net_value),
                    else_=Decimal("0"),
                )
            ),
            Decimal("0"),
        ).label("sales")
        costs_expr = func.coalesce(
            func.sum(
                case(
                    (Invoice.invoice_role == "cost", InvoiceLine.line_net_value),
                    else_=Decimal("0"),
                )
            ),
            Decimal("0"),
        ).label("costs")

        stmt = (
            select(period_label, sales_expr, costs_expr)
            .select_from(InvoiceLine)
            .join(Invoice, InvoiceLine.invoice_id == Invoice.id)
            .where(InvoiceLine.tenant_id == self._tenant_id)
            .group_by(bucket, period_label)
            .order_by(order_expr.asc())
        )
        stmt = self._apply_date_filters(stmt, date_from, date_to)

        result = await self._session.execute(stmt)
        rows = result.all()

        items: list[CashflowItem] = []
        total_sales = Decimal("0")
        total_costs = Decimal("0")

        for row in rows:
            sales = Decimal(row.sales)
            costs = Decimal(row.costs)
            total_sales += sales
            total_costs += costs
            items.append(
                CashflowItem(
                    date=row.date,
                    sales=sales,
                    costs=costs,
                    balance=sales - costs,
                )
            )

        return CashflowResponse(
            items=items,
            total_sales=total_sales,
            total_costs=total_costs,
            total_balance=total_sales - total_costs,
            granularity=granularity,
            date_from=date_from,
            date_to=date_to,
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

    async def get_dashboard(
        self,
        role: str,
        date_from: date | None = None,
        date_to: date | None = None,
        top_limit: int = 10,
    ) -> DashboardResponse:
        summary = await self.get_summary(role=role, date_from=date_from, date_to=date_to)
        trend = await self.get_trend(role=role, date_from=date_from, date_to=date_to)
        previous_trend = None
        if date_from is not None and date_to is not None:
            span_days = (date_to - date_from).days
            from datetime import timedelta

            prev_to = date_from - timedelta(days=1)
            prev_from = prev_to - timedelta(days=span_days)
            previous_trend = await self.get_trend(
                role=role,
                date_from=prev_from,
                date_to=prev_to,
            )
        cost_structure = await self.get_structure(
            role=role, date_from=date_from, date_to=date_to
        )
        cashflow = await self.get_cashflow(date_from=date_from, date_to=date_to)
        top_counterparties = await self.get_top_counterparties(
            role=role,
            limit=top_limit,
            date_from=date_from,
            date_to=date_to,
        )
        return DashboardResponse(
            summary=summary,
            trend=trend,
            previous_trend=previous_trend,
            cost_structure=cost_structure,
            cashflow=cashflow,
            top_counterparties=top_counterparties,
        )
