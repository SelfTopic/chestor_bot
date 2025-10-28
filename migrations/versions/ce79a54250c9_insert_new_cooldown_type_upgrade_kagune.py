"""insert new cooldown type: UPGRADE_KAGUNE

Revision ID: ce79a54250c9
Revises: 80133d7ead4d
Create Date: 2025-10-28 20:26:00.966536

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects.postgresql import insert
from src.database.models import Cooldown

# revision identifiers, used by Alembic.
revision: str = 'ce79a54250c9'
down_revision: Union[str, Sequence[str], None] = '80133d7ead4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    
    op.execute(
        insert(Cooldown).values(
            id=2,
            name="KAGUNE_UPGRADE",
            duration=600    
        ).on_conflict_do_nothing()
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
