"""users.is_service flag for excluding service accounts from analytics

Revision ID: a1f3c7d9e204
Revises: b3f7d1e9a2c6
Create Date: 2026-10-18 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1f3c7d9e204"
down_revision: Union[str, Sequence[str], None] = "b3f7d1e9a2c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_service", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_service")
