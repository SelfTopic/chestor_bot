"""moderation_settings и moderation_actions: настройки модерации чата и журнал действий

Revision ID: feae6d2b3522
Revises: 7c3e9a1f5b20
Create Date: 2026-09-29 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "feae6d2b3522"
down_revision: Union[str, Sequence[str], None] = "7c3e9a1f5b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "moderation_settings",
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "mute_default_seconds", sa.Integer(), server_default="1800", nullable=False
        ),
        sa.Column(
            "ban_default_seconds", sa.Integer(), server_default="1800", nullable=False
        ),
        sa.Column(
            "voice", sa.String(length=16), server_default="neutral", nullable=False
        ),
        sa.Column("admin_chat_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["chat_id"], ["chats.telegram_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("chat_id"),
    )
    op.create_table(
        "moderation_actions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("moderator_id", sa.BigInteger(), nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_moderation_actions_target",
        "moderation_actions",
        ["chat_id", "target_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_moderation_actions_target", table_name="moderation_actions")
    op.drop_table("moderation_actions")
    op.drop_table("moderation_settings")
