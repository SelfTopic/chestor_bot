from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import BigInteger

from .base import Base


class LevelUpLog(Base):
    __tablename__ = "level_up_log"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        nullable=False,
    )

    level: Mapped[int] = mapped_column(
        nullable=False,
    )

    cheston_reward: Mapped[int] = mapped_column(
        nullable=False,
    )

    rc_reward: Mapped[int] = mapped_column(
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
