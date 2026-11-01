"""chat_message_hours — hourly message counters for the rolling chat message top

Revision ID: a3c5e7f9b182
Revises: e7b2c4f9a130
Create Date: 2026-11-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3c5e7f9b182"
down_revision: Union[str, Sequence[str], None] = "e7b2c4f9a130"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_message_hours",
        sa.Column("hour", sa.DateTime(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("messages", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("hour", "chat_id", "user_id"),
    )
    op.create_index(
        "ix_chat_message_hours_chat_hour", "chat_message_hours", ["chat_id", "hour"]
    )
    # Чтобы «неделя» и «месяц» не начинались с нуля: дневные счётчики последних 30 дней
    # ложатся на московскую полночь своего дня (в UTC, как пишет бот).
    op.execute(
        """
        INSERT INTO chat_message_hours (hour, chat_id, user_id, messages)
        SELECT (day::timestamp AT TIME ZONE 'Europe/Moscow') AT TIME ZONE 'UTC',
               chat_id, user_id, messages
        FROM chat_activity
        WHERE chat_type IN ('group', 'supergroup')
          AND day >= (now() AT TIME ZONE 'Europe/Moscow')::date - 30
        """
    )


def downgrade() -> None:
    op.drop_index("ix_chat_message_hours_chat_hour", table_name="chat_message_hours")
    op.drop_table("chat_message_hours")
