"""users.cult_rewarded_at and users.cult_notifications — hourly reward for cult hashtags

Revision ID: e7b2c4f9a130
Revises: d5f1a3c8e620
Create Date: 2026-10-29 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7b2c4f9a130"
down_revision: Union[str, Sequence[str], None] = "d5f1a3c8e620"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("cult_rewarded_at", sa.DateTime(), nullable=True))
    op.add_column(
        "users",
        sa.Column("cult_notifications", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("users", "cult_notifications")
    op.drop_column("users", "cult_rewarded_at")
