"""kagune per-type strength columns + deaths

Revision ID: c1a4e6f9b2d7
Revises: 4d7f2a8e0c93
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1a4e6f9b2d7"
down_revision: Union[str, Sequence[str], None] = "4d7f2a8e0c93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# bit -> новая колонка, см. src/bot/types/kagune.py
_KAGUNE_COLUMNS = {
    1: "kagune_strength_ukaku",
    2: "kagune_strength_koukaku",
    4: "kagune_strength_rinkaku",
    8: "kagune_strength_bikaku",
}


def upgrade() -> None:
    for column in _KAGUNE_COLUMNS.values():
        op.add_column(
            "ghouls", sa.Column(column, sa.Integer(), nullable=True)
        )

    op.add_column(
        "ghouls",
        sa.Column("deaths", sa.Integer(), server_default="0", nullable=False),
    )

    # Сейчас у каждого гуля ровно один открытый тип кагуне - переносим
    # старое общее значение kagune_strength в нужную по kagune_type_bit
    # колонку, ничего не теряя.
    for bit, column in _KAGUNE_COLUMNS.items():
        op.execute(
            f"UPDATE ghouls SET {column} = kagune_strength "
            f"WHERE (kagune_type_bit & {bit}) != 0"
        )

    op.drop_column("ghouls", "kagune_strength")


def downgrade() -> None:
    op.add_column(
        "ghouls",
        sa.Column("kagune_strength", sa.Integer(), server_default="1", nullable=False),
    )

    op.execute(
        "UPDATE ghouls SET kagune_strength = COALESCE("
        "kagune_strength_ukaku, kagune_strength_koukaku, "
        "kagune_strength_rinkaku, kagune_strength_bikaku, 1)"
    )

    op.drop_column("ghouls", "deaths")
    for column in _KAGUNE_COLUMNS.values():
        op.drop_column("ghouls", column)
