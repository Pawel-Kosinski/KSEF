"""Schematy API faktur."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class InvoiceListItem(BaseModel):
    id: UUID
    ksef_number: str | None
    invoice_number: str
    issue_date: date
    sale_date: date | None
    seller_nip: str
    buyer_nip: str
    contractor_name: str | None = None
    invoice_role: str = Field(description="cost = kosztowa, sales = sprzedaż")
    currency_code: str
    total_net: Decimal
    total_vat: Decimal | None = None
    total_gross: Decimal | None = None
    line_count: int


class InvoiceLineRead(BaseModel):
    id: UUID
    line_number: int
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    line_net_value: Decimal
    ai_category_main: str | None = None
    ai_category_sub: str | None = None
    ai_confidence: int | None = None


class InvoiceDetail(BaseModel):
    id: UUID
    ksef_number: str | None
    invoice_number: str
    issue_date: date
    sale_date: date | None
    seller_nip: str
    buyer_nip: str
    contractor_name: str | None = None
    invoice_role: str
    currency_code: str
    total_net: Decimal
    total_vat: Decimal | None = None
    total_gross: Decimal | None = None
    lines: list[InvoiceLineRead]
