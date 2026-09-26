from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class ActiveBattle(Base):
    __tablename__ = "active_battles"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        primary_key=True,
    )

    opponent_telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        nullable=True,
    )

    battle_type: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
