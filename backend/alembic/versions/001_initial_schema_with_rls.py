"""Initial schema: tenants, invoices, invoice_lines + RLS."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("nip", sa.String(length=10), nullable=False),
        sa.Column("ksef_hwm_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nip"),
    )

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ksef_number", sa.String(length=64), nullable=True),
        sa.Column("invoice_number", sa.String(length=64), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("sale_date", sa.Date(), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("seller_nip", sa.String(length=10), nullable=False),
        sa.Column("buyer_nip", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ksef_number"),
    )
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])

    op.create_table(
        "invoice_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=512), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("line_net_value", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("ai_category_main", sa.String(length=128), nullable=True),
        sa.Column("ai_category_sub", sa.String(length=128), nullable=True),
        sa.Column("ai_confidence", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_lines_tenant_product", "invoice_lines", ["tenant_id", "product_name"]
    )
    op.create_index(
        "idx_lines_tenant_invoice", "invoice_lines", ["tenant_id", "invoice_id"]
    )

    # --- Row-Level Security ---
    op.execute("ALTER TABLE invoices ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invoice_lines ENABLE ROW LEVEL SECURITY")

    rls_using = (
        "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::UUID"
    )

    op.execute(
        f"""
        CREATE POLICY tenant_isolation_policy ON invoices
        FOR ALL
        USING ({rls_using})
        WITH CHECK ({rls_using})
        """
    )

    op.execute(
        f"""
        CREATE POLICY tenant_isolation_policy ON invoice_lines
        FOR ALL
        USING ({rls_using})
        WITH CHECK ({rls_using})
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON invoice_lines")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON invoices")
    op.execute("ALTER TABLE invoice_lines DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invoices DISABLE ROW LEVEL SECURITY")

    op.drop_index("idx_lines_tenant_invoice", table_name="invoice_lines")
    op.drop_index("idx_lines_tenant_product", table_name="invoice_lines")
    op.drop_table("invoice_lines")
    op.drop_index("ix_invoices_tenant_id", table_name="invoices")
    op.drop_table("invoices")
    op.drop_table("tenants")
