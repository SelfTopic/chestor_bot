"""death_log table + ghouls.is_dead / lifetime_rc_earned

Revision ID: 8e2c5f7a1d94
Revises: c1a4e6f9b2d7
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8e2c5f7a1d94"
down_revision: Union[str, Sequence[str], None] = "c1a4e6f9b2d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ghouls",
        sa.Column("is_dead", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "ghouls",
        sa.Column(
            "lifetime_rc_earned", sa.Integer(), server_default="0", nullable=False
        ),
    )

    op.create_table(
        "death_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("cause", sa.String(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("lifetime_rc_earned", sa.Integer(), nullable=False),
        sa.Column("killer_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("death_log")
    op.drop_column("ghouls", "lifetime_rc_earned")
    op.drop_column("ghouls", "is_dead")
