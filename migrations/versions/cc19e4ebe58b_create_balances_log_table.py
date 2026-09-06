"""create balances_log table

Revision ID: cc19e4ebe58b
Revises: ce79a54250c9
Create Date: 2026-09-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc19e4ebe58b"
down_revision: Union[str, Sequence[str], None] = "ce79a54250c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "balances_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("change_balance", sa.Integer(), nullable=False),
        sa.Column("before_balance", sa.Integer(), nullable=False),
        sa.Column("after_balance", sa.Integer(), nullable=False),
        sa.Column("log", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("balances_log")
