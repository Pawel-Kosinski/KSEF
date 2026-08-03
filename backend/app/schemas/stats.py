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
