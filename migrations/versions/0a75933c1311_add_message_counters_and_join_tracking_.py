"""add message counters and join tracking to chat_participants

Revision ID: 0a75933c1311
Revises: affa837f35b3
Create Date: 2026-09-13 17:18:03.161966

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a75933c1311"
down_revision: Union[str, Sequence[str], None] = "affa837f35b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "chat_participants",
        sa.Column(
            "messages_total", sa.Integer(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "chat_participants",
        sa.Column(
            "messages_today", sa.Integer(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "chat_participants",
        sa.Column("messages_week", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "chat_participants",
        sa.Column(
            "messages_month", sa.Integer(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "chat_participants", sa.Column("joined_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "chat_participants", sa.Column("join_method", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("chat_participants", "join_method")
    op.drop_column("chat_participants", "joined_at")
    op.drop_column("chat_participants", "messages_month")
    op.drop_column("chat_participants", "messages_week")
    op.drop_column("chat_participants", "messages_today")
    op.drop_column("chat_participants", "messages_total")
