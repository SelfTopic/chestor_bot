from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class RouletteMachine(Base):
    __tablename__ = "roulette_machines"
    # У игрока в чате открыт один автомат, даже если он дважды нажал разом.
    __table_args__ = (
        Index(
            "uq_roulette_machines_open_owner",
            "chat_id",
            "telegram_id",
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(User.telegram_id, ondelete="CASCADE"), nullable=False
    )
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    # Положение ленты: по нему закрытый после перезапуска автомат показывает, где она стояла.
    position: Mapped[int] = mapped_column(nullable=False)
    opened_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    closed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
