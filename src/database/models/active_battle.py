from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class ActiveBattle(Base):
    """Эфемерный лок "этот гуль сейчас занят боем" - ОДНА строка на
    telegram_id (PK - именно telegram_id, а не отдельный autoincrement id).
    Ровно это не даёт гулю оказаться сразу в двух боях одновременно (см.
    чат: эксплойт "пригласить себя с твинка на дуэль и одновременно
    затеять бой с мобом", чтобы фактически не потерять HP по одному из
    двух исходов) - вторая попытка занять уже занятый telegram_id упрётся
    в PK-конфликт на уровне БД, а не в состояние гонки в коде.

    Строка удаляется, когда бой разрешён (см.
    BattleRecordService.release) - это НЕ история (для истории см.
    `Battle`), а только "занят прямо сейчас"."""

    __tablename__ = "active_battles"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        primary_key=True,
    )

    # NULL для боя с мобом (у моба нет своей строки User) - заполнено для
    # дуэли (telegram_id второго участника).
    opponent_telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        nullable=True,
    )

    battle_type: Mapped[str] = mapped_column(nullable=False)  # "mob" | "duel"
    status: Mapped[str] = mapped_column(nullable=False)  # "pending_confirmation" | "active"

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
