"""roast_log: огрызания бота через нейросеть

Revision ID: 7c3e9a1f5b20
Revises: 5b8e1d2c7a40
Create Date: 2026-09-29 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c3e9a1f5b20"
down_revision: Union[str, Sequence[str], None] = "5b8e1d2c7a40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roast_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("context", sa.String(), nullable=False),
        sa.Column("facts", sa.String(), nullable=False),
        sa.Column("reply", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("filtered", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("bot_message_id", sa.BigInteger(), nullable=True),
        sa.Column("followups", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roast_log_bot_message", "roast_log", ["chat_id", "bot_message_id"])
    op.create_index(
        "ix_roast_log_argument", "roast_log", ["chat_id", "telegram_id", "created_at"]
    )
    op.create_index("ix_roast_log_created_at", "roast_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_roast_log_created_at", table_name="roast_log")
    op.drop_index("ix_roast_log_argument", table_name="roast_log")
    op.drop_index("ix_roast_log_bot_message", table_name="roast_log")
    op.drop_table("roast_log")
