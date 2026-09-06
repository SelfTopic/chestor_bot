from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import BigInteger

from .base import Base


class BalancesLog(Base):
    __tablename__ = "balances_log"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    change_balance: Mapped[int] = mapped_column(
        nullable=False,
    )

    before_balance: Mapped[int] = mapped_column(
        nullable=False,
    )

    after_balance: Mapped[int] = mapped_column(
        nullable=False,
    )

    log: Mapped[str] = mapped_column(
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
