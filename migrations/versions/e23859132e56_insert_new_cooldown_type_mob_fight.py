"""insert new cooldown type: MOB_FIGHT

Revision ID: e23859132e56
Revises: 77d894e50c04
Create Date: 2026-09-13 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.postgresql import insert

from src.database.models import Cooldown

# revision identifiers, used by Alembic.
revision: str = "e23859132e56"
down_revision: Union[str, Sequence[str], None] = "77d894e50c04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 10 минут - BATTLE_DESIGN.md "Формула левел-апа" ("Фарм мобов (раз в
    # 10 минут...)").
    op.execute(
        insert(Cooldown)
        .values(id=6, name="MOB_FIGHT", duration=600)
        .on_conflict_do_nothing()
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
