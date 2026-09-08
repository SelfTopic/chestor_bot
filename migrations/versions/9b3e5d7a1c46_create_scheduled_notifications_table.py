"""create scheduled_notifications table

Revision ID: 9b3e5d7a1c46
Revises: 7a2e9c4f6b18
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b3e5d7a1c46"
down_revision: Union[str, Sequence[str], None] = "7a2e9c4f6b18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("notification_type", sa.String(), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=True),
        sa.Column("fire_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["telegram_id"], ["users.telegram_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "telegram_id", "notification_type", name="uq_notification_telegram_type"
        ),
    )
    op.create_index(
        "ix_scheduled_notifications_fire_at",
        "scheduled_notifications",
        ["fire_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_notifications_fire_at", "scheduled_notifications")
    op.drop_table("scheduled_notifications")
