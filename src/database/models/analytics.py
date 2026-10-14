from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BotEvent(Base):
    __tablename__ = "bot_events"
    __table_args__ = (
        Index("ix_bot_events_handler_at", "handler", "at"),
        Index("ix_bot_events_user_at", "user_id", "at"),
        Index("ix_bot_events_chat_at", "chat_id", "at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now(), index=True)
    handler: Mapped[str] = mapped_column(String(64), nullable=False)
    update_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    chat_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    duration_ms: Mapped[int] = mapped_column(nullable=False, default=0)


class ChatActivity(Base):
    __tablename__ = "chat_activity"

    day: Mapped[date] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_type: Mapped[str] = mapped_column(String(16), nullable=False)
    messages: Mapped[int] = mapped_column(nullable=False, default=0)
