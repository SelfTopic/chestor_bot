"""users.last_active_at for retention/churn — any update from the user, not just chat messages

Revision ID: c8a4f1e6b935
Revises: a1f3c7d9e204
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8a4f1e6b935"
down_revision: Union[str, Sequence[str], None] = "a1f3c7d9e204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_active_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_active_at")
