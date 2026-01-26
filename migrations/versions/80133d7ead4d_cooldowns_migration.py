"""cooldowns_migration

Revision ID: 80133d7ead4d
Revises:
Create Date: 2025-08-16 03:17:50.829892

"""

import logging
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.postgresql import insert

from src.database.models import Cooldown

logger = logging.getLogger(__name__)

logger.debug("Logger is configure")

# revision identifiers, used by Alembic.
revision: str = "80133d7ead4d"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        insert(Cooldown)
        .values(id=1, name="SNAP", duration=600)
        .on_conflict_do_nothing()
    )

    op.execute(
        insert(Cooldown)
        .values(id=4, name="COFFEE", duration=1800)
        .on_conflict_do_nothing()
    )

    op.execute(
        insert(Cooldown)
        .values(id=3, name="COFFEE_DAY", duration=86400)
        .on_conflict_do_nothing()
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
