from .base import Base 

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column 
from sqlalchemy.types import BigInteger

from datetime import datetime


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

    snap_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False    
    ) 

    kagune_type_bit: Mapped[int] = mapped_column(
        nullable=False
    )

    kagune_strength: Mapped[int] = mapped_column(
        default=1,
        nullable=False     
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

    coffee_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False     
    )

    hunger: Mapped[int] = mapped_column(
        default=100,
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
