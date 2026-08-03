"""Modele danych wyekstrahowanych z faktury FA(3)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class Fa3InvoiceHeader(BaseModel):
    """Metadane nagłówka FA(3) – wymagane do zapisu tabeli invoices."""

    invoice_number: str = Field(description="P_2")
    issue_date: date = Field(description="P_1")
    sale_date: date | None = Field(default=None, description="P_6")
    seller_nip: str
    buyer_nip: str
    seller_name: str | None = Field(default=None, description="Podmiot1 / DaneIdentyfikacyjne / Nazwa")
    buyer_name: str | None = Field(default=None, description="Podmiot2 / DaneIdentyfikacyjne / Nazwa")
    currency_code: str = "PLN"
    total_net: Decimal | None = Field(default=None, description="Suma netto (P_13_*)")
    total_vat: Decimal | None = Field(default=None, description="Suma VAT (P_14_*)")
    total_gross: Decimal | None = Field(default=None, description="Kwota brutto (P_15)")


class Fa3InvoiceLine(BaseModel):
    """Pojedynczy wiersz //tns:Fa/tns:FaWiersz."""

    line_number: int
    product_name: str = Field(description="P_7 – nazwa towaru/usługi")
    quantity: Decimal = Field(description="P_8B – ilość")
    unit_price: Decimal = Field(description="P_9A – cena jednostkowa netto")
    line_net_value: Decimal = Field(description="P_11 – wartość netto wiersza")


class Fa3ParseResult(BaseModel):
    """Wynik parsowania pliku XML FA(3)."""

    namespace: str
    header: Fa3InvoiceHeader
    lines: list[Fa3InvoiceLine]
