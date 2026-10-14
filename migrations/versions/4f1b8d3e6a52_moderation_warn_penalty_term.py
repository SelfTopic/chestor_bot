"""moderation_settings: свой срок наказания на лимите варнов

Revision ID: 4f1b8d3e6a52
Revises: 8e4a2c6b0d13
Create Date: 2026-10-13 21:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f1b8d3e6a52"
down_revision: Union[str, Sequence[str], None] = "8e4a2c6b0d13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "moderation_settings",
        sa.Column("warn_penalty_seconds", sa.Integer(), server_default="1800", nullable=True),
    )


def downgrade() -> None:
    op.drop_column("moderation_settings", "warn_penalty_seconds")
