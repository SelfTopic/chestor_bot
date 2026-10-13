from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.bot.types.moderation import ModerationActionType, ModerationVoice, WarnPenalty

from .base import Base
from .chat import Chat


def _values(enum: type[Enum]) -> list[str]:
    return [member.value for member in enum]


# Строкой, а не типом Postgres: новое значение не потребует ALTER TYPE.
def _string_enum(enum: type[Enum]) -> SqlEnum:
    return SqlEnum(enum, native_enum=False, length=16, values_callable=_values)


class ModerationSettings(Base):
    __tablename__ = "moderation_settings"
    # Чат админов служит только одному чату.
    __table_args__ = (
        Index("uq_moderation_settings_admin_chat", "admin_chat_id", unique=True),
    )

    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(Chat.telegram_id, ondelete="CASCADE"),
        primary_key=True,
    )

    # NULL — навсегда.
    mute_default_seconds: Mapped[Optional[int]] = mapped_column(
        nullable=True, server_default="1800"
    )
    ban_default_seconds: Mapped[Optional[int]] = mapped_column(
        nullable=True, server_default="1800"
    )
    voice: Mapped[ModerationVoice] = mapped_column(
        _string_enum(ModerationVoice),
        nullable=False,
        server_default=ModerationVoice.NEUTRAL.value,
    )
    warn_limit: Mapped[int] = mapped_column(nullable=False, server_default="3")
    warn_penalty: Mapped[WarnPenalty] = mapped_column(
        _string_enum(WarnPenalty),
        nullable=False,
        server_default=WarnPenalty.MUTE.value,
    )
    # Срок мута или бана на лимите варнов; NULL — навсегда.
    warn_penalty_seconds: Mapped[Optional[int]] = mapped_column(
        nullable=True, server_default="1800"
    )
    # NULL — варны не сгорают.
    warn_expiry_seconds: Mapped[Optional[int]] = mapped_column(
        nullable=True, server_default="604800"
    )
    admin_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    # Запрошенный отсюда чат админов: привязка появится, когда его подтвердят там.
    admin_chat_request: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)


class ModerationAction(Base):
    __tablename__ = "moderation_actions"
    __table_args__ = (
        Index("ix_moderation_actions_target", "chat_id", "target_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[ModerationActionType] = mapped_column(
        _string_enum(ModerationActionType), nullable=False
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    # Конец мута или бана со сроком: его объявляет тикер.
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)
    expiry_notified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class ModerationWarning(Base):
    __tablename__ = "moderation_warnings"
    __table_args__ = (Index("ix_moderation_warnings_target", "chat_id", "target_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    # NULL — не сгорает.
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    # Снят вручную или сброшен наказанием на лимите.
    revoked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    expiry_notified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
