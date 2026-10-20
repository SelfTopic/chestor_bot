"""level_up_log table — mirrors death_log, so growth curve is reconstructible like death is

Сейчас у живого гуля видно только текущий уровень: как быстро он качался и где прогресс
застыл, не восстановить. Для каждого уровня — источник (бой/моб/промо/админ), награды.

Revision ID: b7e9c2f5d618
Revises: f4d2a8c6e103
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e9c2f5d618"
down_revision: Union[str, Sequence[str], None] = "f4d2a8c6e103"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "level_up_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("cheston_reward", sa.Integer(), nullable=False),
        sa.Column("rc_reward", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_level_up_log_telegram_id_created_at",
        "level_up_log",
        ["telegram_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_level_up_log_telegram_id_created_at", table_name="level_up_log")
    op.drop_table("level_up_log")
