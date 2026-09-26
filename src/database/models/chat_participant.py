from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .chat import Chat
from .user import User


class ChatParticipant(Base):
    __tablename__ = "chat_participants"

    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Chat.telegram_id, ondelete="CASCADE"),
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        primary_key=True,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    messages_total: Mapped[int] = mapped_column(nullable=False, default=0)
    messages_today: Mapped[int] = mapped_column(nullable=False, default=0)
    messages_week: Mapped[int] = mapped_column(nullable=False, default=0)
    messages_month: Mapped[int] = mapped_column(nullable=False, default=0)

    joined_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    join_method: Mapped[Optional[str]] = mapped_column(nullable=True)
