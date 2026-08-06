"""RLS na contractor_category_rules – izolacja tenantów."""

from typing import Sequence, Union

from alembic import op

revision: str = "010_rls_contractor_rules"
down_revision: Union[str, None] = "009_tenant_industry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RLS_USING = (
    "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::UUID"
)


def upgrade() -> None:
    op.execute("ALTER TABLE contractor_category_rules ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_policy ON contractor_category_rules
        FOR ALL
        USING ({RLS_USING})
        WITH CHECK ({RLS_USING})
        """
    )
    op.execute("ALTER TABLE contractor_category_rules FORCE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON contractor_category_rules")
    op.execute("ALTER TABLE contractor_category_rules NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE contractor_category_rules DISABLE ROW LEVEL SECURITY")
