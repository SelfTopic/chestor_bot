"""arcade_videos — the chart video cache becomes shared by all arcade machines

Revision ID: d1f3a5b7c912
Revises: c7e9a1b3d505
Create Date: 2026-11-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1f3a5b7c912"
down_revision: Union[str, Sequence[str], None] = "c7e9a1b3d505"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("chart_videos", "arcade_videos")
    op.execute("ALTER INDEX chart_videos_pkey RENAME TO arcade_videos_pkey")


def downgrade() -> None:
    op.execute("ALTER INDEX arcade_videos_pkey RENAME TO chart_videos_pkey")
    op.rename_table("arcade_videos", "chart_videos")
