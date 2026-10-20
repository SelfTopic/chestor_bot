"""users.balance and balances_log amount columns: integer -> bigint

god-mode аккаунт на проде уже упёрся в INT32-max, families.balance изначально bigint.

Revision ID: f4d2a8c6e103
Revises: c8a4f1e6b935
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4d2a8c6e103"
down_revision: Union[str, Sequence[str], None] = "c8a4f1e6b935"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BALANCES_LOG_COLUMNS = ("change_balance", "before_balance", "after_balance")


def upgrade() -> None:
    op.alter_column("users", "balance", existing_type=sa.Integer(), type_=sa.BigInteger())
    for column in BALANCES_LOG_COLUMNS:
        op.alter_column(
            "balances_log", column, existing_type=sa.Integer(), type_=sa.BigInteger()
        )


def downgrade() -> None:
    op.alter_column("users", "balance", existing_type=sa.BigInteger(), type_=sa.Integer())
    for column in BALANCES_LOG_COLUMNS:
        op.alter_column(
            "balances_log", column, existing_type=sa.BigInteger(), type_=sa.Integer()
        )
