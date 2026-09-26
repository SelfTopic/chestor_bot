from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class DuelSession(Base):
    __tablename__ = "duel_sessions"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    is_private_origin: Mapped[bool] = mapped_column(nullable=False, default=False)

    initiator_telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.telegram_id, ondelete="CASCADE"), nullable=False
    )
    target_telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.telegram_id, ondelete="CASCADE"), nullable=False
    )

    stage: Mapped[str] = mapped_column(nullable=False, default="awaiting_consent")

    initiator_consented: Mapped[bool] = mapped_column(nullable=False, default=False)
    target_consented: Mapped[bool] = mapped_column(nullable=False, default=False)

    favored_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    compress_hp: Mapped[Optional[bool]] = mapped_column(nullable=True)

    consent_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    outcome_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    winner_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    loser_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    winner_choice: Mapped[Optional[str]] = mapped_column(nullable=True)

    ended_naturally: Mapped[Optional[bool]] = mapped_column(nullable=True)

    reward_level_progress: Mapped[Optional[float]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
