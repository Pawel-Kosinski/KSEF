"""tenant_categories + RLS."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_tenant_categories"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_CATEGORIES = [
    ("Materiały i Surowce", 1),
    ("Opakowania", 2),
    ("Paliwa i Transport", 3),
    ("Koszty Biurowe i IT", 4),
    ("Usługi Zewnętrzne", 5),
    ("Inne Koszty Operacyjne", 6),
]


def upgrade() -> None:
    op.create_table(
        "tenant_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_categories_tenant_id", "tenant_categories", ["tenant_id"])
    op.create_index(
        "idx_tenant_categories_tenant_name",
        "tenant_categories",
        ["tenant_id", "name"],
        unique=True,
    )

    op.execute("ALTER TABLE tenant_categories ENABLE ROW LEVEL SECURITY")

    rls_using = (
        "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::UUID"
    )
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_policy ON tenant_categories
        FOR ALL
        USING ({rls_using})
        WITH CHECK ({rls_using})
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON tenant_categories")
    op.execute("ALTER TABLE tenant_categories DISABLE ROW LEVEL SECURITY")
    op.drop_index("idx_tenant_categories_tenant_name", table_name="tenant_categories")
    op.drop_index("ix_tenant_categories_tenant_id", table_name="tenant_categories")
    op.drop_table("tenant_categories")
