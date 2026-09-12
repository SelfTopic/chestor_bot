"""add battle outcome columns

Revision ID: 8f8ecf3f99ee
Revises: 8f01e072f133
Create Date: 2026-09-12 17:53:10.881065

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f8ecf3f99ee"
down_revision: Union[str, Sequence[str], None] = "8f01e072f133"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Причина/исход/награда - механики, которых в коде ещё нет (засада
    # моба "3b", ЛС-выбор победителя "ограбить/отпустить/съесть" - см.
    # BATTLE_DESIGN.md "Исход боя") - колонки заводятся заранее, тем же
    # приёмом, что Ghoul.is_dead/deaths были заведены до самого движка.
    op.add_column(
        "battles",
        sa.Column(
            "is_forced", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )
    op.add_column("battles", sa.Column("winner_choice", sa.String(), nullable=True))
    op.add_column(
        "battles", sa.Column("reward_level_progress", sa.Float(), nullable=True)
    )
    op.add_column("battles", sa.Column("reward_rc", sa.Integer(), nullable=True))
    op.add_column("battles", sa.Column("reward_balance", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("battles", "reward_balance")
    op.drop_column("battles", "reward_rc")
    op.drop_column("battles", "reward_level_progress")
    op.drop_column("battles", "winner_choice")
    op.drop_column("battles", "is_forced")
