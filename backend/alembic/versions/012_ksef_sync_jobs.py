"""Tabela zadań synchronizacji KSeF (tło) + RLS."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_ksef_sync_jobs"
down_revision: Union[str, None] = "011_invoices_issue_date_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RLS_USING = (
    "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::UUID"
)


def upgrade() -> None:
    op.create_table(
        "ksef_sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("progress_message", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ksef_sync_jobs_tenant_id", "ksef_sync_jobs", ["tenant_id"])

    op.execute("ALTER TABLE ksef_sync_jobs ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_policy ON ksef_sync_jobs
        FOR ALL
        USING ({RLS_USING})
        WITH CHECK ({RLS_USING})
        """
    )
    op.execute("ALTER TABLE ksef_sync_jobs FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON ksef_sync_jobs")
    op.execute("ALTER TABLE ksef_sync_jobs NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ksef_sync_jobs DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_ksef_sync_jobs_tenant_id", table_name="ksef_sync_jobs")
    op.drop_table("ksef_sync_jobs")
