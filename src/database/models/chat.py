from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import BigInteger

from .base import Base


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(
        primary_key=True, 
        autoincrement=True     
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger, 
        nullable=False, 
        unique=True 
    )

    title: Mapped[str] = mapped_column(
        nullable=True
    )

    rules: Mapped[str] = mapped_column(
        nullable=True
    )

    welcome_message: Mapped[str] = mapped_column(
        nullable=True
    )

    goodbye_message: Mapped[str] = mapped_column(
        nullable=True
    )

    username: Mapped[str] = mapped_column(
        nullable=True,
        default=None
    )

    creator_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now()
    )
