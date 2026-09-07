"""insert new cooldown type: EAT_HUMAN

Revision ID: 7a2e9c4f6b18
Revises: 1f6d3a9c8b21
Create Date: 2026-09-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.postgresql import insert

from src.database.models import Cooldown

# revision identifiers, used by Alembic.
revision: str = "7a2e9c4f6b18"
down_revision: Union[str, Sequence[str], None] = "1f6d3a9c8b21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        insert(Cooldown)
        .values(id=5, name="EAT_HUMAN", duration=86400)
        .on_conflict_do_nothing()
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
