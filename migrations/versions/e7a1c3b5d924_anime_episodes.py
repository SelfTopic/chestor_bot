"""anime_episodes: file_id серий аниме для /anime без лимита загрузки в 50 МБ

Revision ID: e7a1c3b5d924
Revises: c4d8a2f6e913
Create Date: 2026-10-14 22:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a1c3b5d924"
down_revision: Union[str, Sequence[str], None] = "c4d8a2f6e913"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "anime_episodes",
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("episode", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.String(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=False),
        sa.Column("added_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("season", "episode"),
    )


def downgrade() -> None:
    op.drop_table("anime_episodes")
