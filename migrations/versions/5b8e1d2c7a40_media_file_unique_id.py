"""media.file_unique_id for /remove_gif

Revision ID: 5b8e1d2c7a40
Revises: 0a75933c1311
Create Date: 2026-09-28 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b8e1d2c7a40"
down_revision: Union[str, Sequence[str], None] = "0a75933c1311"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("media", sa.Column("file_unique_id", sa.String(), nullable=True))
    op.create_index("ix_media_file_unique_id", "media", ["file_unique_id"])


def downgrade() -> None:
    op.drop_index("ix_media_file_unique_id", table_name="media")
    op.drop_column("media", "file_unique_id")
