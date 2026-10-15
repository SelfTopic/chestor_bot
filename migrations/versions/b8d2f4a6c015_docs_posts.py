"""docs_posts: какой раздел документации каким постом опубликован в канале

Revision ID: b8d2f4a6c015
Revises: a5c9e1d3b704
Create Date: 2026-10-15 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8d2f4a6c015"
down_revision: Union[str, Sequence[str], None] = "a5c9e1d3b704"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "docs_posts",
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("channel", "slug"),
    )


def downgrade() -> None:
    op.drop_table("docs_posts")
