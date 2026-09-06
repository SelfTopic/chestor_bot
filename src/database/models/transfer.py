from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
    )

    sender_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        nullable=False,
    )

    receiver_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
