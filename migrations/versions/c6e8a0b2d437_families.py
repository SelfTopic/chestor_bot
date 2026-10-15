"""families: семьи (браки любого размера), их члены, предложения и согласия на брак

Revision ID: c6e8a0b2d437
Revises: b8d2f4a6c015
Create Date: 2026-10-15 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6e8a0b2d437"
down_revision: Union[str, Sequence[str], None] = "b8d2f4a6c015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "families",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("balance", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("dissolved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "family_members",
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["telegram_id"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("telegram_id"),
    )
    op.create_index("ix_family_members_family_id", "family_members", ["family_id"])
    op.create_table(
        "marriage_proposals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("proposer_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("target_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("declined_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["proposer_telegram_id"], ["users.telegram_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_telegram_id"], ["users.telegram_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_marriage_proposals_stage", "marriage_proposals", ["stage"])
    op.create_table(
        "marriage_consents",
        sa.Column("proposal_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["marriage_proposals.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("proposal_id", "telegram_id"),
    )


def downgrade() -> None:
    op.drop_table("marriage_consents")
    op.drop_index("ix_marriage_proposals_stage", table_name="marriage_proposals")
    op.drop_table("marriage_proposals")
    op.drop_index("ix_family_members_family_id", table_name="family_members")
    op.drop_table("family_members")
    op.drop_table("families")
