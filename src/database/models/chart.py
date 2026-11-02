from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class ChartMachine(Base):
    __tablename__ = "chart_machines"
    # Открытый автомат в чате один: второй открыть нельзя, даже если двое нажали разом.
    __table_args__ = (
        Index(
            "uq_chart_machines_open_chat",
            "chat_id",
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    opened_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.telegram_id, ondelete="CASCADE"), nullable=False
    )
    opened_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    closed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class ChartRound(Base):
    __tablename__ = "chart_rounds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    machine_id: Mapped[int] = mapped_column(
        ForeignKey(ChartMachine.id, ondelete="CASCADE"), nullable=False, index=True
    )
    crash: Mapped[int] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    settled_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class ChartBet(Base):
    __tablename__ = "chart_bets"
    __table_args__ = (UniqueConstraint("round_id", "telegram_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    round_id: Mapped[int] = mapped_column(
        ForeignKey(ChartRound.id, ondelete="CASCADE"), nullable=False
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.telegram_id, ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target: Mapped[Optional[int]] = mapped_column(nullable=True)
    cashed_at: Mapped[Optional[int]] = mapped_column(nullable=True)
    payout: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    placed_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())


class ChartCrashVideo(Base):
    __tablename__ = "chart_crash_videos"

    multiplier: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    file_id: Mapped[str] = mapped_column(nullable=False)
    added_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
