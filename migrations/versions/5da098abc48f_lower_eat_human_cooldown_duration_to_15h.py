"""lower eat_human cooldown duration to 15h

Revision ID: 5da098abc48f
Revises: e23859132e56
Create Date: 2026-09-13 03:25:53.623936

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import update

from src.database.models import Cooldown

# revision identifiers, used by Alembic.
revision: str = '5da098abc48f'
down_revision: Union[str, Sequence[str], None] = 'e23859132e56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        update(Cooldown).where(Cooldown.name == "EAT_HUMAN").values(duration=54000)
    )


def downgrade() -> None:
    op.execute(
        update(Cooldown).where(Cooldown.name == "EAT_HUMAN").values(duration=86400)
    )
