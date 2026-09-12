"""create duel_sessions table

Revision ID: 38d74612b3e5
Revises: 8f8ecf3f99ee
Create Date: 2026-09-12 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "38d74612b3e5"
down_revision: Union[str, Sequence[str], None] = "8f8ecf3f99ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # "Разговорное" состояние одной дуэли (кто кого позвал, в каком чате,
    # на какой стадии) - отдельно от ActiveBattle (эфемерный лок "занят
    # прямо сейчас") и Battle (постоянная история, пишется только когда
    # исход уже известен целиком). См. duel_session.py.
    op.create_table(
        "duel_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("initiator_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("target_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "stage", sa.String(), server_default="awaiting_consent", nullable=False
        ),
        sa.Column(
            "initiator_consented",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "target_consented",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("favored_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("compress_hp", sa.Boolean(), nullable=True),
        sa.Column("consent_message_id", sa.BigInteger(), nullable=True),
        sa.Column("outcome_message_id", sa.BigInteger(), nullable=True),
        sa.Column("winner_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("loser_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("winner_choice", sa.String(), nullable=True),
        sa.Column("ended_naturally", sa.Boolean(), nullable=True),
        sa.Column("reward_level_progress", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["initiator_telegram_id"], ["users.telegram_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_telegram_id"], ["users.telegram_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("duel_sessions")
