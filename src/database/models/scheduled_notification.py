from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .user import User


class ScheduledNotification(Base):
    """Один активный запланированный пуш на пару (гуль, тип уведомления).

    Не история - строка переиспользуется (upsert) при каждом пересчёте
    расписания, см. GhoulService.materialize_passive_stats и
    BATTLE_DESIGN.md ("Механизм regen/hunger")."""

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

    # Только для notification_type=hunger_threshold (75/50/25/0). NULL для
    # остальных типов (например health_full).
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
