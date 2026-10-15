"""family_renames: смена имени семьи с согласия всех её членов

Revision ID: d7f9b1c3e548
Revises: c6e8a0b2d437
Create Date: 2026-10-15 21:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d7f9b1c3e548"
down_revision: Union[str, Sequence[str], None] = "c6e8a0b2d437"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "family_renames",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("proposer_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("consented", postgresql.ARRAY(sa.BigInteger()), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("declined_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_family_renames_family_id", "family_renames", ["family_id"])
    op.create_index("ix_family_renames_stage", "family_renames", ["stage"])


def downgrade() -> None:
    op.drop_index("ix_family_renames_stage", table_name="family_renames")
    op.drop_index("ix_family_renames_family_id", table_name="family_renames")
    op.drop_table("family_renames")
