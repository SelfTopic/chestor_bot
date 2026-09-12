"""create active_battles and battles tables

Revision ID: 8f01e072f133
Revises: 8e2c5f7a1d94
Create Date: 2026-09-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f01e072f133"
down_revision: Union[str, Sequence[str], None] = "8e2c5f7a1d94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # active_battles - эфемерный лок "занят прямо сейчас" (PK = telegram_id,
    # не отдельный id) - не даёт гулю оказаться в двух боях одновременно
    # (см. BATTLE_ENGINE.md, чат про эксплойт "твинк + бой с мобом
    # одновременно"). Строки удаляются, когда бой разрешён.
    op.create_table(
        "active_battles",
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("opponent_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("battle_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["telegram_id"], ["users.telegram_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["opponent_telegram_id"], ["users.telegram_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("telegram_id"),
    )

    # battles - постоянная история (BATTLE_ENGINE.md 5.1) - и дуэлей, и
    # боёв с мобами. participant_b_telegram_id/mob_name взаимоисключающие
    # по смыслу (дуэль/моб).
    op.create_table(
        "battles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("battle_type", sa.String(), nullable=False),
        sa.Column("participant_a_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("participant_b_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("mob_name", sa.String(), nullable=True),
        sa.Column("winner", sa.String(), nullable=True),
        sa.Column("ended_naturally", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["participant_a_telegram_id"], ["users.telegram_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["participant_b_telegram_id"], ["users.telegram_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_battles_participant_a_created_at",
        "battles",
        ["participant_a_telegram_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_battles_participant_b_created_at",
        "battles",
        ["participant_b_telegram_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_battles_participant_b_created_at", table_name="battles")
    op.drop_index("ix_battles_participant_a_created_at", table_name="battles")
    op.drop_table("battles")
    op.drop_table("active_battles")
