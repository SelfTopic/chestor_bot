"""add level_progress to ghouls

Revision ID: 4d7f2a8e0c93
Revises: 9b3e5d7a1c46
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d7f2a8e0c93"
down_revision: Union[str, Sequence[str], None] = "9b3e5d7a1c46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ghouls",
        sa.Column(
            "level_progress",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("ghouls", "level_progress")
