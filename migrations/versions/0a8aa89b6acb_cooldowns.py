"""cooldowns

Revision ID: 0a8aa89b6acb
Revises: ce79a54250c9
Create Date: 2026-08-07 09:23:31.151996

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a8aa89b6acb'
down_revision: Union[str, Sequence[str], None] = 'ce79a54250c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
