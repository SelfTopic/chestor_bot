from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import BigInteger

from .base import Base


class Ghoul(Base):
    __tablename__ = "ghouls"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        unique=True 
    )

    rc_money: Mapped[int] = mapped_column(
        nullable=False,
        default=0    
    )

    level: Mapped[int] = mapped_column(
        default=1,
        nullable=False
    )

    level_progress: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False
    )

    snap_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False    
    ) 

    kagune_type_bit: Mapped[int] = mapped_column(
        nullable=True
    )

    # Сила по каждому типу кагуне отдельно - NULL значит тип не открыт.
    # Типов ровно 4 (лор-константа), отдельная таблица не нужна - см.
    # BATTLE_DESIGN.md ("Хранение силы по типам кагуне").
    kagune_strength_ukaku: Mapped[Optional[int]] = mapped_column(
        nullable=True
    )

    kagune_strength_koukaku: Mapped[Optional[int]] = mapped_column(
        nullable=True
    )

    kagune_strength_rinkaku: Mapped[Optional[int]] = mapped_column(
        nullable=True
    )

    kagune_strength_bikaku: Mapped[Optional[int]] = mapped_column(
        nullable=True
    )

    strength: Mapped[int] = mapped_column(
        default=1,
        nullable=False    
    )

    dexterity: Mapped[int] = mapped_column(
        default=1,
        nullable=False     
    )

    speed: Mapped[int] = mapped_column(
        default=1,
        nullable=False     
    )

    health: Mapped[int] = mapped_column(
        default=5,
        nullable=False
    )

    health_updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False
    )

    max_health: Mapped[int] = mapped_column(
        default=5,
        nullable=False
    )

    regeneration: Mapped[int] = mapped_column(
        default=1,
        nullable=False
    )

    eat_humans: Mapped[int] = mapped_column(
        default=0,
        nullable=False     
    )

    eat_ghouls: Mapped[int] = mapped_column(
        default=0,
        nullable=False     
    )

    is_kakuja: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )

    # Единственное (вместе с id/created_at), что переживает сброс при
    # смерти - см. BATTLE_DESIGN.md ("Смерть и сброс"). Сама логика сброса
    # ещё не реализована, колонка заводится заранее.
    deaths: Mapped[int] = mapped_column(
        default=0,
        nullable=False
    )

    coffee_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False     
    )

    hunger: Mapped[int] = mapped_column(
        default=100,
        nullable=False
    )

    hunger_updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False    
    )

    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False
    )
