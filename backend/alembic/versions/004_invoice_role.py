"""Dodaje invoice_role (cost | sales) do invoices."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_invoice_role"
down_revision: Union[str, None] = "003_force_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column(
            "invoice_role",
            sa.String(length=16),
            nullable=False,
            server_default="cost",
            comment="cost = nabywca (Subject2), sales = sprzedawca (Subject1)",
        ),
    )
    op.create_index("ix_invoices_tenant_role", "invoices", ["tenant_id", "invoice_role"])

    # Backfill: sprzedawca = tenant NIP → sales
    op.execute(
        """
        UPDATE invoices i
        SET invoice_role = 'sales'
        FROM tenants t
        WHERE i.tenant_id = t.id AND i.seller_nip = t.nip
        """
    )


def downgrade() -> None:
    op.drop_index("ix_invoices_tenant_role", table_name="invoices")
    op.drop_column("invoices", "invoice_role")
