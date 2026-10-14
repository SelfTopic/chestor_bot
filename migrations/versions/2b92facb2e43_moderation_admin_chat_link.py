"""moderation_settings: запрос на привязку чата админов, чат админов — одному чату

Revision ID: 2b92facb2e43
Revises: a0c6b75e25eb
Create Date: 2026-09-29 22:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b92facb2e43"
down_revision: Union[str, Sequence[str], None] = "a0c6b75e25eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "moderation_settings",
        sa.Column("admin_chat_request", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "uq_moderation_settings_admin_chat",
        "moderation_settings",
        ["admin_chat_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_moderation_settings_admin_chat", table_name="moderation_settings")
    op.drop_column("moderation_settings", "admin_chat_request")
