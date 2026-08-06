"""Indeks (tenant_id, issue_date) – filtry dashboardu po dacie."""

from typing import Sequence, Union

from alembic import op

revision: str = "011_invoices_issue_date_index"
down_revision: Union[str, None] = "010_rls_contractor_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_invoices_tenant_issue_date",
        "invoices",
        ["tenant_id", "issue_date"],
    )
    op.create_index(
        "ix_invoices_tenant_role_issue_date",
        "invoices",
        ["tenant_id", "invoice_role", "issue_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_invoices_tenant_role_issue_date", table_name="invoices")
    op.drop_index("ix_invoices_tenant_issue_date", table_name="invoices")
