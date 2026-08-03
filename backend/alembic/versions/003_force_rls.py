"""FORCE ROW LEVEL SECURITY – właściciel tabeli nie omija RLS."""

from typing import Sequence, Union

from alembic import op

revision: str = "003_force_rls"
down_revision: Union[str, None] = "002_tenant_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("invoices", "invoice_lines", "tenant_categories")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
