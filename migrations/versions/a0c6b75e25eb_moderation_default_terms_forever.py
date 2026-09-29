"""moderation_settings: срок по умолчанию может быть «навсегда» (NULL)

Revision ID: a0c6b75e25eb
Revises: feae6d2b3522
Create Date: 2026-09-29 21:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0c6b75e25eb"
down_revision: Union[str, Sequence[str], None] = "feae6d2b3522"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ("mute_default_seconds", "ban_default_seconds")


def upgrade() -> None:
    for column in COLUMNS:
        op.alter_column(
            "moderation_settings", column, existing_type=sa.Integer(), nullable=True
        )


def downgrade() -> None:
    for column in COLUMNS:
        op.execute(
            f"UPDATE moderation_settings SET {column} = 1800 WHERE {column} IS NULL"
        )
        op.alter_column(
            "moderation_settings", column, existing_type=sa.Integer(), nullable=False
        )
