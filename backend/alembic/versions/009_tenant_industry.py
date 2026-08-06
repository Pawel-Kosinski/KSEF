"""Migracja: pole industry na tenants (Smart Onboarding)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_tenant_industry"
down_revision: Union[str, None] = "008_contractor_category_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "industry",
            sa.String(length=512),
            nullable=True,
            comment="Branża / opis działalności firmy (onboarding)",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "industry")
