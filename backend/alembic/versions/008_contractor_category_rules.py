"""Migracja: reguły kategorii kontrahentów + źródło kategoryzacji na liniach."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_contractor_category_rules"
down_revision: Union[str, None] = "007_encrypted_ksef_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contractor_category_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contractor_nip", sa.String(length=10), nullable=False),
        sa.Column("contractor_name", sa.String(length=255), nullable=True),
        sa.Column("category_main", sa.String(length=128), nullable=False),
        sa.Column("category_sub", sa.String(length=128), nullable=False, server_default="Inne"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "contractor_nip", name="uq_contractor_rule_tenant_nip"),
    )
    op.create_index(
        "ix_contractor_rules_tenant_nip",
        "contractor_category_rules",
        ["tenant_id", "contractor_nip"],
    )

    op.add_column(
        "invoice_lines",
        sa.Column(
            "category_source",
            sa.String(length=16),
            nullable=True,
            comment="ai | rule | user | fallback",
        ),
    )
    op.add_column(
        "invoices",
        sa.Column("primary_category_main", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("primary_category_sub", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("primary_category_source", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "primary_category_source")
    op.drop_column("invoices", "primary_category_sub")
    op.drop_column("invoices", "primary_category_main")
    op.drop_column("invoice_lines", "category_source")
    op.drop_index("ix_contractor_rules_tenant_nip", table_name="contractor_category_rules")
    op.drop_table("contractor_category_rules")
