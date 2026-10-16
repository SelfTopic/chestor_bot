"""promo_codes, promo_activations: промокоды (удалённые остаются в истории) и кто их активировал

Revision ID: b3f7d1e9a2c6
Revises: e9b1c3d5f760
Create Date: 2026-10-16 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b3f7d1e9a2c6"
down_revision: Union[str, Sequence[str], None] = "e9b1c3d5f760"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("rewards", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("activations_limit", sa.Integer(), nullable=False),
        sa.Column("activations_used", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_promo_codes_live_name",
        "promo_codes",
        ["name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "promo_activations",
        sa.Column("promo_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("activated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["promo_id"], ["promo_codes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("promo_id", "telegram_id"),
    )


def downgrade() -> None:
    op.drop_table("promo_activations")
    op.drop_index("uq_promo_codes_live_name", table_name="promo_codes")
    op.drop_table("promo_codes")
