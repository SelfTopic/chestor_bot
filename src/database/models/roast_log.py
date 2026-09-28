from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RoastLog(Base):
    __tablename__ = "roast_log"
    __table_args__ = (
        Index("ix_roast_log_bot_message", "chat_id", "bot_message_id"),
        Index("ix_roast_log_argument", "chat_id", "telegram_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    first_name: Mapped[str] = mapped_column(nullable=False)

    message: Mapped[str] = mapped_column(nullable=False)
    context: Mapped[str] = mapped_column(nullable=False)
    facts: Mapped[str] = mapped_column(nullable=False, default="")

    reply: Mapped[Optional[str]] = mapped_column(nullable=True)
    model: Mapped[str] = mapped_column(nullable=False)
    filtered: Mapped[bool] = mapped_column(nullable=False, default=False)
    latency_ms: Mapped[int] = mapped_column(nullable=False, default=0)

    bot_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    followups: Mapped[int] = mapped_column(nullable=False, default=0)
    rating: Mapped[Optional[int]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), index=True
    )
