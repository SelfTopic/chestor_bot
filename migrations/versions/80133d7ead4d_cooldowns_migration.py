"""cooldowns_migration

Revision ID: 80133d7ead4d
Revises: 
Create Date: 2025-08-16 03:17:50.829892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from src.database.models import Cooldown
import logging

logger = logging.getLogger(__name__)

logger.debug("Logger is configure")

# revision identifiers, used by Alembic.
revision: str = '80133d7ead4d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    logger.info("Run migration insert cooldown SNAP")
    op.execute(
        insert(Cooldown).values(
            id=1,
            name="SNAP",
            duration=600    
        ).on_conflict_do_nothing()
    )
    logger.info("Migration insert cooldown snap sucsessful passed")


def downgrade() -> None:
    """Downgrade schema."""
    pass

upgrade()