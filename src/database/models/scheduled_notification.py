from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class ScheduledNotification(Base):
    __tablename__ = "scheduled_notifications"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.telegram_id, ondelete="CASCADE"),
        nullable=False,
    )

    notification_type: Mapped[str] = mapped_column(
        nullable=False,
    )

    threshold: Mapped[Optional[int]] = mapped_column(
        nullable=True,
    )

    fire_at: Mapped[datetime] = mapped_column(
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "telegram_id", "notification_type", name="uq_notification_telegram_type"
        ),
    )
