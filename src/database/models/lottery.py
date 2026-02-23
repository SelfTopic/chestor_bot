from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class Lottery(Base):
    __tablename__ = "lotteries"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        nullable=False,
    )

    bet_amount: Mapped[int] = mapped_column(
        nullable=False,
    )

    chosen_color: Mapped[str] = mapped_column(
        nullable=False,
    )

    winning_color: Mapped[str] = mapped_column(
        nullable=False,
    )

    is_won: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    earned: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    video_file_id: Mapped[str | None] = mapped_column(
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
