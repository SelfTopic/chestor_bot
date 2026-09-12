from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class Battle(Base):
    """Постоянная история завершённых боёв (BATTLE_ENGINE.md 5.1) - и
    дуэлей, и боёв с мобами в одной таблице. `participant_b_telegram_id`
    (дуэль) и `mob_name` (бой с мобом) взаимоисключающие по смыслу - у
    моба нет строки `User`, поэтому вместо телеграм-id только имя для
    истории. `winner` - "a"/"b"/None, та же схема, что уже несёт
    `BattleResult.winner` в самом движке (не выдумываем новую)."""

    __tablename__ = "battles"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    battle_type: Mapped[str] = mapped_column(nullable=False)  # "mob" | "duel"

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

    winner: Mapped[Optional[str]] = mapped_column(nullable=True)  # "a" | "b" | None (ничья)
    ended_naturally: Mapped[bool] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
