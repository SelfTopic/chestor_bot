"""link_media_cache: file_id видео и фотокаруселей по ссылкам

Revision ID: 9b3e7d1c5a20
Revises: 6a9c2e4f8b17
Create Date: 2026-10-14 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9b3e7d1c5a20"
down_revision: Union[str, Sequence[str], None] = "6a9c2e4f8b17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "link_media_cache",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("video_file_id", sa.String(), nullable=True),
        sa.Column(
            "photo_file_ids",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("audio_file_id", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("link_media_cache")
