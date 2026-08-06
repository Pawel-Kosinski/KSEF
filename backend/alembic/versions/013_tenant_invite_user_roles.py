"""invite_token na tenants + role na users (multi-user SaaS)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_tenant_invite_user_roles"
down_revision: Union[str, None] = "012_ksef_sync_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("invite_token", sa.String(length=36), nullable=True),
    )
    op.execute(
        "UPDATE tenants SET invite_token = gen_random_uuid()::text WHERE invite_token IS NULL"
    )
    op.alter_column("tenants", "invite_token", nullable=False)
    op.create_unique_constraint("uq_tenants_invite_token", "tenants", ["invite_token"])

    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=16),
            nullable=False,
            server_default="user",
        ),
    )
    op.execute("UPDATE users SET role = 'admin'")
    op.alter_column("users", "role", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "role")
    op.drop_constraint("uq_tenants_invite_token", "tenants", type_="unique")
    op.drop_column("tenants", "invite_token")
