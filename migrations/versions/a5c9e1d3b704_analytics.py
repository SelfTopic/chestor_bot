"""bot_events, chat_activity: статистика — команды бота и сообщения в чатах по дням

Revision ID: a5c9e1d3b704
Revises: f2b6d8e0a347
Create Date: 2026-10-15 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a5c9e1d3b704"
down_revision: Union[str, Sequence[str], None] = "f2b6d8e0a347"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bot_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("handler", sa.String(length=64), nullable=False),
        sa.Column("update_kind", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=True),
        sa.Column("chat_type", sa.String(length=16), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bot_events_at", "bot_events", ["at"])
    op.create_index("ix_bot_events_handler_at", "bot_events", ["handler", "at"])
    op.create_index("ix_bot_events_user_at", "bot_events", ["user_id", "at"])
    op.create_index("ix_bot_events_chat_at", "bot_events", ["chat_id", "at"])
    op.create_table(
        "chat_activity",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_type", sa.String(length=16), nullable=False),
        sa.Column("messages", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("day", "chat_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("chat_activity")
    op.drop_index("ix_bot_events_chat_at", table_name="bot_events")
    op.drop_index("ix_bot_events_user_at", table_name="bot_events")
    op.drop_index("ix_bot_events_handler_at", table_name="bot_events")
    op.drop_index("ix_bot_events_at", table_name="bot_events")
    op.drop_table("bot_events")
