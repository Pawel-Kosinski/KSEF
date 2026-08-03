"""Endpointy statystyk analitycznych (Faza 4)."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.tenant import TenantContext, get_current_tenant, get_rls_session
from app.schemas.stats import (
    CostStructureResponse,
    SummaryResponse,
    TopCounterpartiesResponse,
    TrendResponse,
)
from app.services.analytics.statistics import StatisticsService

router = APIRouter(prefix="/stats", tags=["Statystyki"])

InvoiceRole = Literal["cost", "sales"]


def _statistics_service(
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_rls_session),
) -> StatisticsService:
    return StatisticsService(session, tenant.tenant_id)


@router.get("/summary", response_model=SummaryResponse)
async def period_summary(
    role: InvoiceRole = Query(default="cost", description="cost = koszty, sales = sprzedaż"),
    date_from: date | None = Query(default=None, description="Początek zakresu (P_1)"),
    date_to: date | None = Query(default=None, description="Koniec zakresu (P_1)"),
    service: StatisticsService = Depends(_statistics_service),
) -> SummaryResponse:
    return await service.get_summary(role=role, date_from=date_from, date_to=date_to)


@router.get("/cost-structure", response_model=CostStructureResponse)
async def cost_structure(
    role: InvoiceRole = Query(default="cost", description="cost = koszty, sales = sprzedaż"),
    date_from: date | None = Query(default=None, description="Początek zakresu (P_1)"),
    date_to: date | None = Query(default=None, description="Koniec zakresu (P_1)"),
    service: StatisticsService = Depends(_statistics_service),
) -> CostStructureResponse:
    return await service.get_structure(role=role, date_from=date_from, date_to=date_to)


@router.get("/trend", response_model=TrendResponse)
async def spending_trend(
    role: InvoiceRole = Query(default="cost", description="cost = koszty, sales = sprzedaż"),
    date_from: date | None = Query(default=None, description="Początek zakresu (P_1)"),
    date_to: date | None = Query(default=None, description="Koniec zakresu (P_1)"),
    service: StatisticsService = Depends(_statistics_service),
) -> TrendResponse:
    return await service.get_trend(role=role, date_from=date_from, date_to=date_to)


@router.get("/top-counterparties", response_model=TopCounterpartiesResponse)
async def top_counterparties(
    role: InvoiceRole = Query(default="cost", description="cost = dostawcy, sales = klienci"),
    limit: int = Query(default=10, ge=1, le=10, description="Liczba kontrahentów (max 10)"),
    date_from: date | None = Query(default=None, description="Początek zakresu (P_1)"),
    date_to: date | None = Query(default=None, description="Koniec zakresu (P_1)"),
    service: StatisticsService = Depends(_statistics_service),
) -> TopCounterpartiesResponse:
    return await service.get_top_counterparties(
        role=role,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
    )


# Zachowanie wsteczne – top dostawcy = koszty
@router.get("/top-vendors", response_model=TopCounterpartiesResponse)
async def top_vendors(
    limit: int = Query(default=10, ge=1, le=10),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    service: StatisticsService = Depends(_statistics_service),
) -> TopCounterpartiesResponse:
    return await service.get_top_counterparties(
        role="cost",
        limit=limit,
        date_from=date_from,
        date_to=date_to,
    )
