"""add is_private_origin to duel_sessions

Revision ID: 77d894e50c04
Revises: 38d74612b3e5
Create Date: 2026-09-13 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "77d894e50c04"
down_revision: Union[str, Sequence[str], None] = "38d74612b3e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Дуэль, вызванная из ЛС инициатора с ботом (соперник указан через
    # @username без общего группового чата) - chat_id бесполезен для
    # "чтобы все видели": это приватный чат ровно между инициатором и
    # ботом, соперник в нём не состоит (найдено как баг при ревью).
    op.add_column(
        "duel_sessions",
        sa.Column(
            "is_private_origin", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("duel_sessions", "is_private_origin")
