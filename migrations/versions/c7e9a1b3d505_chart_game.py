"""chart_game — machines, rounds, bets and crash video cache of the chart game

Revision ID: c7e9a1b3d505
Revises: b4d6f8a0c293
Create Date: 2026-11-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e9a1b3d505"
down_revision: Union[str, Sequence[str], None] = "b4d6f8a0c293"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chart_machines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("opened_by", sa.BigInteger(), nullable=False),
        sa.Column("opened_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["opened_by"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_chart_machines_open_chat",
        "chart_machines",
        ["chat_id"],
        unique=True,
        postgresql_where=sa.text("closed_at IS NULL"),
    )
    op.create_table(
        "chart_rounds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("machine_id", sa.Integer(), nullable=False),
        sa.Column("crash", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("settled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["machine_id"], ["chart_machines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chart_rounds_machine_id", "chart_rounds", ["machine_id"])
    op.create_table(
        "chart_bets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("round_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("target", sa.Integer(), nullable=True),
        sa.Column("cashed_at", sa.Integer(), nullable=True),
        sa.Column("payout", sa.BigInteger(), nullable=False),
        sa.Column("placed_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["round_id"], ["chart_rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["telegram_id"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("round_id", "telegram_id"),
    )
    op.create_table(
        "chart_crash_videos",
        sa.Column("multiplier", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("file_id", sa.String(), nullable=False),
        sa.Column("added_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("multiplier"),
    )


def downgrade() -> None:
    op.drop_table("chart_crash_videos")
    op.drop_table("chart_bets")
    op.drop_index("ix_chart_rounds_machine_id", table_name="chart_rounds")
    op.drop_table("chart_rounds")
    op.drop_index("uq_chart_machines_open_chat", table_name="chart_machines")
    op.drop_table("chart_machines")
