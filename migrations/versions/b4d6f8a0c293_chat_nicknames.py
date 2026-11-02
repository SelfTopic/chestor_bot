"""chat_nicknames — per-chat player nicknames

Revision ID: b4d6f8a0c293
Revises: a3c5e7f9b182
Create Date: 2026-11-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4d6f8a0c293"
down_revision: Union[str, Sequence[str], None] = "a3c5e7f9b182"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_nicknames",
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("nickname", sa.String(length=32), nullable=False),
        sa.Column("set_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.telegram_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["telegram_id"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chat_id", "telegram_id"),
    )


def downgrade() -> None:
    op.drop_table("chat_nicknames")
