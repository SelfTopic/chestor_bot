from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import BigInteger

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)

    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    username: Mapped[str] = mapped_column(nullable=True, unique=True)

    race_bit: Mapped[int] = mapped_column(nullable=False, default=0)

    balance: Mapped[int] = mapped_column(nullable=False, default=0)

    energy: Mapped[int] = mapped_column(nullable=False, default=100)

    energy_consumption: Mapped[int] = mapped_column(nullable=False, default=25)

    happyness: Mapped[int] = mapped_column(nullable=False, default=100)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    is_banned: Mapped[bool] = mapped_column(nullable=False, default=False)
    ban_reason: Mapped[Optional[str]] = mapped_column(nullable=True)
    banned_until: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    has_private_chat: Mapped[bool] = mapped_column(nullable=False, default=False)

    @property
    def full_name(self) -> str:
        return self.first_name + " " + (self.last_name or "")
