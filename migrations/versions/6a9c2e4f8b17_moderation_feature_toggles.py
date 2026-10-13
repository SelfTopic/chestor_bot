"""moderation_settings: выключатели функций модерации

Revision ID: 6a9c2e4f8b17
Revises: 4f1b8d3e6a52
Create Date: 2026-10-14 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a9c2e4f8b17"
down_revision: Union[str, Sequence[str], None] = "4f1b8d3e6a52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "moderation_settings",
        sa.Column("mute_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "moderation_settings",
        sa.Column("ban_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "moderation_settings",
        sa.Column("kick_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "moderation_settings",
        sa.Column("warns_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "moderation_settings",
        sa.Column("notices_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("moderation_settings", "notices_enabled")
    op.drop_column("moderation_settings", "warns_enabled")
    op.drop_column("moderation_settings", "kick_enabled")
    op.drop_column("moderation_settings", "ban_enabled")
    op.drop_column("moderation_settings", "mute_enabled")
