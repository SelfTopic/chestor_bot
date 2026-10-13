"""moderation: окончание мута, бана и варна по сроку объявляет тикер

Revision ID: 8e4a2c6b0d13
Revises: 3d5f7a9c1e2b
Create Date: 2026-10-13 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8e4a2c6b0d13"
down_revision: Union[str, Sequence[str], None] = "3d5f7a9c1e2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("moderation_actions", sa.Column("expires_at", sa.DateTime(), nullable=True))
    op.add_column(
        "moderation_actions", sa.Column("expiry_notified_at", sa.DateTime(), nullable=True)
    )
    op.create_index(
        "ix_moderation_actions_expires_at", "moderation_actions", ["expires_at"]
    )
    op.add_column(
        "moderation_warnings", sa.Column("expiry_notified_at", sa.DateTime(), nullable=True)
    )
    # Сроки уже выданных мутов и банов; всё, что кончилось до выкатки, считается
    # объявленным — иначе тикер при первом запуске разослал бы старьё.
    op.execute(
        "UPDATE moderation_actions SET expires_at = created_at"
        " + duration_seconds * interval '1 second'"
        " WHERE action IN ('mute', 'ban') AND duration_seconds IS NOT NULL"
    )
    op.execute(
        "UPDATE moderation_actions SET expiry_notified_at = now() WHERE expires_at <= now()"
    )
    op.execute(
        "UPDATE moderation_warnings SET expiry_notified_at = now() WHERE expires_at <= now()"
    )


def downgrade() -> None:
    op.drop_column("moderation_warnings", "expiry_notified_at")
    op.drop_index("ix_moderation_actions_expires_at", table_name="moderation_actions")
    op.drop_column("moderation_actions", "expiry_notified_at")
    op.drop_column("moderation_actions", "expires_at")
