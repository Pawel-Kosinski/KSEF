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
    primary_category_main: str | None = None
    primary_category_sub: str | None = None
    primary_category_source: str | None = Field(
        default=None,
        description="ai | rule | user | fallback",
    )


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
    category_source: str | None = Field(
        default=None,
        description="ai | rule | user | fallback",
    )


class InvoiceLineCategoryUpdateResponse(BaseModel):
    id: UUID
    line_number: int
    ai_category_main: str | None
    ai_category_sub: str | None
    ai_confidence: int | None
    category_source: str | None
    invoice_primary_category_main: str | None = None
    invoice_primary_category_sub: str | None = None
    invoice_primary_category_source: str | None = None
    rule_saved: bool = False
    contractor_nip: str | None = None


class InvoiceLineCategoryUpdate(BaseModel):
    category_main: str = Field(min_length=1, max_length=128)
    category_sub: str | None = Field(default=None, max_length=128)
    learn_rule: bool = Field(
        default=False,
        description="Zapisz regułę NIP kontrahenta dla przyszłych faktur",
    )


class InvoiceCategoryUpdate(BaseModel):
    category_main: str = Field(min_length=1, max_length=128)
    category_sub: str | None = Field(default=None, max_length=128)


class InvoiceCategoryUpdateResponse(BaseModel):
    id: UUID
    primary_category_main: str | None
    primary_category_sub: str | None
    primary_category_source: str | None


class CategoryListResponse(BaseModel):
    categories: list[str]


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
    primary_category_main: str | None = None
    primary_category_sub: str | None = None
    primary_category_source: str | None = None
    lines: list[InvoiceLineRead]
