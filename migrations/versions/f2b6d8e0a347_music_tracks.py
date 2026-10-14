"""music_tracks: file_id треков, отправленных по «песня …»

Revision ID: f2b6d8e0a347
Revises: e7a1c3b5d924
Create Date: 2026-10-15 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2b6d8e0a347"
down_revision: Union[str, Sequence[str], None] = "e7a1c3b5d924"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "music_tracks",
        sa.Column("track_id", sa.String(), nullable=False),
        sa.Column("file_id", sa.String(), nullable=False),
        sa.Column("added_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("track_id"),
    )


def downgrade() -> None:
    op.drop_table("music_tracks")
