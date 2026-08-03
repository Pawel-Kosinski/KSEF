"""Dodaje contractor_name i sumy VAT/brutto na invoices."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_contractor_and_totals"
down_revision: Union[str, None] = "004_invoice_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column(
            "contractor_name",
            sa.String(length=255),
            nullable=True,
            comment="Nazwa kontrahenta (sprzedawca dla kosztów, nabywca dla sprzedaży)",
        ),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "total_net",
            sa.Numeric(18, 2),
            nullable=True,
            comment="Suma netto z nagłówka FA (P_13_*)",
        ),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "total_vat",
            sa.Numeric(18, 2),
            nullable=True,
            comment="Suma VAT z nagłówka FA (P_14_*)",
        ),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "total_gross",
            sa.Numeric(18, 2),
            nullable=True,
            comment="Kwota brutto / należność ogółem (P_15)",
        ),
    )

    # Backfill netto z pozycji dla istniejących faktur
    op.execute(
        """
        UPDATE invoices i
        SET total_net = sub.sum_net
        FROM (
            SELECT invoice_id, SUM(line_net_value) AS sum_net
            FROM invoice_lines
            GROUP BY invoice_id
        ) sub
        WHERE i.id = sub.invoice_id AND i.total_net IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("invoices", "total_gross")
    op.drop_column("invoices", "total_vat")
    op.drop_column("invoices", "total_net")
    op.drop_column("invoices", "contractor_name")
