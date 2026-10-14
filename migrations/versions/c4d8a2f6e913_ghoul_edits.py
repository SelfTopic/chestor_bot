"""ghoul_edits: эдиты по «Токийскому гулю» из каналов, file_id для «1000-7»

Revision ID: c4d8a2f6e913
Revises: 9b3e7d1c5a20
Create Date: 2026-10-14 20:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d8a2f6e913"
down_revision: Union[str, Sequence[str], None] = "9b3e7d1c5a20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ghoul_edits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_id", sa.String(), nullable=False),
        sa.Column("file_unique_id", sa.String(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=False),
        sa.Column("added_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "channel_message_id"),
        sa.UniqueConstraint("file_unique_id"),
    )


def downgrade() -> None:
    op.drop_table("ghoul_edits")
