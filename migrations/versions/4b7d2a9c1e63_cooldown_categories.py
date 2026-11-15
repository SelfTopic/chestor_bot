"""add cooldown categories

Revision ID: 4b7d2a9c1e63
Revises: e3a5c7d9f124
Create Date: 2026-11-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4b7d2a9c1e63"
down_revision: Union[str, Sequence[str], None] = "e3a5c7d9f124"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cooldowns",
        sa.Column("category", sa.String(length=20), server_default="user", nullable=False),
    )
    op.execute(
        sa.text(
            "UPDATE cooldowns SET category = 'ghoul' "
            "WHERE name IN ('SNAP', 'COFFEE', 'COFFEE_DAY', 'KAGUNE_UPGRADE', "
            "'EAT_HUMAN', 'MOB_FIGHT')"
        )
    )


def downgrade() -> None:
    op.drop_column("cooldowns", "category")
