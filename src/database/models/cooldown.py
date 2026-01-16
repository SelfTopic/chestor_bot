from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import BigInteger

from .base import Base


class Cooldown(Base):
    __tablename__ = "cooldowns"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True    
    )

    name: Mapped[str] = mapped_column(
        nullable=False    
    )

    description: Mapped[str] = mapped_column(
        nullable=True
    )

    duration: Mapped[int] = mapped_column(
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