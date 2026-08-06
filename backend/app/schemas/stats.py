"""Schematy odpowiedzi API statystyk (Faza 4 – analityka opisowa)."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

TrendGranularity = Literal["day", "week", "month"]


class CostStructureItem(BaseModel):
    """Pojedyncza pozycja wykresu kołowego (Donut Chart)."""

    category: str = Field(description="kategoria_glowna przypisana przez AI")
    total_net: Decimal = Field(description="Suma wartości netto (P_11) w PLN")


class CostStructureResponse(BaseModel):
    items: list[CostStructureItem]
    total_net: Decimal
    date_from: date | None = None
    date_to: date | None = None
    role: str | None = None


class TrendItem(BaseModel):
    """Pojedynczy punkt wykresu trendu."""

    period: str = Field(description="Okres: YYYY-MM-DD, YYYY-Www lub YYYY-MM")
    total_net: Decimal


class TrendResponse(BaseModel):
    items: list[TrendItem]
    total_net: Decimal
    granularity: TrendGranularity = "month"
    date_from: date | None = None
    date_to: date | None = None
    role: str | None = None
    category: str | None = None


class CashflowItem(BaseModel):
    """Pojedynczy punkt wykresu cashflow (przychody vs koszty)."""

    date: str = Field(description="Okres: YYYY-MM-DD, YYYY-Www lub YYYY-MM")
    sales: Decimal = Field(description="Suma przychodów netto (invoice_role=sales)")
    costs: Decimal = Field(description="Suma kosztów netto (invoice_role=cost)")
    balance: Decimal = Field(description="Saldo: sales - costs")


class CashflowResponse(BaseModel):
    items: list[CashflowItem]
    total_sales: Decimal
    total_costs: Decimal
    total_balance: Decimal
    granularity: TrendGranularity = "month"
    date_from: date | None = None
    date_to: date | None = None


class TopCounterpartyItem(BaseModel):
    counterparty_nip: str
    contractor_name: str | None = None
    ksef_number: str | None = None
    total_net: Decimal
    rank: int


class TopCounterpartiesResponse(BaseModel):
    items: list[TopCounterpartyItem]
    limit: int
    date_from: date | None = None
    date_to: date | None = None
    role: str | None = None


class SummaryResponse(BaseModel):
    total_net: Decimal = Field(description="Suma netto w okresie")
    total_vat: Decimal = Field(description="Suma VAT w okresie")
    total_gross: Decimal = Field(description="Suma brutto w okresie")
    date_from: date | None = None
    date_to: date | None = None
    role: str | None = None


class DashboardResponse(BaseModel):
    """Zagregowane dane dashboardu – jedno żądanie zamiast wielu."""

    summary: SummaryResponse
    trend: TrendResponse
    previous_trend: TrendResponse | None = None
    cost_structure: CostStructureResponse
    cashflow: CashflowResponse
    top_counterparties: TopCounterpartiesResponse
