"""create chat_participants table

Revision ID: affa837f35b3
Revises: 5da098abc48f
Create Date: 2026-09-13 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "affa837f35b3"
down_revision: Union[str, Sequence[str], None] = "5da098abc48f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # "Кто вообще писал в этом чате" - Bot API не даёт список участников
    # чата целиком ни одним методом, только косвенно через апдейты. Пишется
    # при каждом сообщении в группе (SyncEntitiesService.sync), читается
    # командой "выбери участника" (fun_router.py). Композитный PK сам
    # служит уникальным индексом под ON CONFLICT DO UPDATE.
    op.create_table(
        "chat_participants",
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "last_seen_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["chat_id"], ["chats.telegram_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["telegram_id"], ["users.telegram_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("chat_id", "telegram_id"),
    )


def downgrade() -> None:
    op.drop_table("chat_participants")
