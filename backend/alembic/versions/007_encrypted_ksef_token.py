"""Migracja: encrypted_ksef_token na tenants."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_encrypted_ksef_token"
down_revision: Union[str, None] = "006_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("encrypted_ksef_token", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "encrypted_ksef_token")
