"""Helpery ETL – dominująca kategoria na nagłówku faktury."""

from decimal import Decimal

from app.database.models import Invoice, InvoiceLine


def update_invoice_primary_category(invoice: Invoice, lines: list[InvoiceLine]) -> None:
    if not lines:
        return
    dominant = max(lines, key=lambda line: line.line_net_value or Decimal("0"))
    invoice.primary_category_main = dominant.ai_category_main
    invoice.primary_category_sub = dominant.ai_category_sub
    invoice.primary_category_source = dominant.category_source
