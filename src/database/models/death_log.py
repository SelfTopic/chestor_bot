from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import BigInteger

from .base import Base


class DeathLog(Base):
    """Историческая запись о смерти - в отличие от сброса/is_dead на самом
    Ghoul, эта строка никогда не перезаписывается и не теряется. См.
    BATTLE_DESIGN.md ("Смерть и сброс")."""

    __tablename__ = "death_log"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    cause: Mapped[str] = mapped_column(
        nullable=False,
    )
    """"starvation" | "eaten" - те же два триггера, что в "Смерть и сброс"."""

    level: Mapped[int] = mapped_column(
        nullable=False,
    )

    lifetime_rc_earned: Mapped[int] = mapped_column(
        nullable=False,
    )

    killer_telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    """Кто съел - только для cause="eaten", NULL для голодной смерти."""

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
