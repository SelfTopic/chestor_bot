from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class Battle(Base):
    __tablename__ = "battles"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    battle_type: Mapped[str] = mapped_column(nullable=False)

    participant_a_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        nullable=False,
    )

    participant_b_telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        nullable=True,
    )

    mob_name: Mapped[Optional[str]] = mapped_column(nullable=True)

    winner: Mapped[Optional[str]] = mapped_column(nullable=True)
    ended_naturally: Mapped[bool] = mapped_column(nullable=False)

    is_forced: Mapped[bool] = mapped_column(nullable=False, default=False)

    winner_choice: Mapped[Optional[str]] = mapped_column(nullable=True)

    reward_level_progress: Mapped[Optional[float]] = mapped_column(nullable=True)
    reward_rc: Mapped[Optional[int]] = mapped_column(nullable=True)
    reward_balance: Mapped[Optional[int]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
