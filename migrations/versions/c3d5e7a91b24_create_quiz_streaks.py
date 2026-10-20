"""create quiz_streaks

Revision ID: c3d5e7a91b24
Revises: b7e9c2f5d618
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d5e7a91b24"
down_revision: Union[str, Sequence[str], None] = "b7e9c2f5d618"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quiz_streaks",
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("rich", sa.String(), nullable=False),
        sa.Column("streak", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["telegram_id"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("telegram_id"),
    )
    op.create_index("ix_quiz_streaks_expires_at", "quiz_streaks", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_quiz_streaks_expires_at", table_name="quiz_streaks")
    op.drop_table("quiz_streaks")
