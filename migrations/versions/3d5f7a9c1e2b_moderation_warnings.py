"""moderation: варны и их настройки в чате

Revision ID: 3d5f7a9c1e2b
Revises: 2b92facb2e43
Create Date: 2026-10-13 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d5f7a9c1e2b"
down_revision: Union[str, Sequence[str], None] = "2b92facb2e43"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "moderation_settings",
        sa.Column("warn_limit", sa.Integer(), server_default="3", nullable=False),
    )
    op.add_column(
        "moderation_settings",
        sa.Column(
            "warn_penalty", sa.String(length=16), server_default="mute", nullable=False
        ),
    )
    op.add_column(
        "moderation_settings",
        sa.Column("warn_expiry_seconds", sa.Integer(), server_default="604800", nullable=True),
    )
    op.create_table(
        "moderation_warnings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("moderator_id", sa.BigInteger(), nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_moderation_warnings_target", "moderation_warnings", ["chat_id", "target_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_moderation_warnings_target", table_name="moderation_warnings")
    op.drop_table("moderation_warnings")
    op.drop_column("moderation_settings", "warn_expiry_seconds")
    op.drop_column("moderation_settings", "warn_penalty")
    op.drop_column("moderation_settings", "warn_limit")
