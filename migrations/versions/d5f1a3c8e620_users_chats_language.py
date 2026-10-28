"""users.language, users.telegram_language and chats.language — the language the bot speaks

Existing players and chats keep Russian; new ones start from the Telegram language.
users.telegram_language is kept for background messages, which have no update to read it from.

Revision ID: d5f1a3c8e620
Revises: c3d5e7a91b24
Create Date: 2026-10-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5f1a3c8e620"
down_revision: Union[str, Sequence[str], None] = "c3d5e7a91b24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("language", sa.String(), nullable=True))
    op.add_column("users", sa.Column("telegram_language", sa.String(), nullable=True))
    op.add_column("chats", sa.Column("language", sa.String(), nullable=True))
    op.execute("UPDATE users SET language = 'ru'")
    op.execute("UPDATE chats SET language = 'ru'")


def downgrade() -> None:
    op.drop_column("chats", "language")
    op.drop_column("users", "telegram_language")
    op.drop_column("users", "language")
