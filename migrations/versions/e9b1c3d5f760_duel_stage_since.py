"""duel_sessions.stage_since: когда дуэль перешла на нынешнюю стадию

Срок стадии (согласие, фора, выбор победителя) считается от этого времени в базе, а не
от момента, когда тикер впервые увидел дуэль: перезапуск бота сроки больше не сбрасывает.

Revision ID: e9b1c3d5f760
Revises: d7f9b1c3e548
Create Date: 2026-10-16 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9b1c3d5f760"
down_revision: Union[str, Sequence[str], None] = "d7f9b1c3e548"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "duel_sessions",
        sa.Column("stage_since", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("duel_sessions", "stage_since")
