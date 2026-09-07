"""add health_updated_at and hunger_updated_at to ghouls

Revision ID: 1f6d3a9c8b21
Revises: ccbc066a7cdd
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1f6d3a9c8b21"
down_revision: Union[str, Sequence[str], None] = "ccbc066a7cdd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ghouls",
        sa.Column(
            "health_updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "ghouls",
        sa.Column(
            "hunger_updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("ghouls", "hunger_updated_at")
    op.drop_column("ghouls", "health_updated_at")
