from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Optional

from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.orm import aliased
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import Chat, ModerationAction, ModerationSettings, ModerationWarning, User
from ..types import ModerationActionType, ModerationVoice
from .base import Base


TIMED_ACTIONS = (ModerationActionType.MUTE, ModerationActionType.BAN)


@dataclass(frozen=True)
class DueExpiration:
    # MUTE и BAN — кончился срок наказания, WARN — сгорели варны.
    kind: ModerationActionType
    chat_id: int
    target_id: int
    first_name: Optional[str]
    chat_title: Optional[str]
    voice: ModerationVoice
    admin_chat_id: Optional[int]
    warns_left: int = 0
    warn_limit: int = 0


class ModerationRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def settings(self, chat_id: int) -> ModerationSettings:
        # Строка заводится при первом обращении: значения по умолчанию — в схеме.
        await self.session.execute(
            insert(ModerationSettings)
            .values(chat_id=chat_id)
            .on_conflict_do_nothing(index_elements=["chat_id"])
        )
        settings = await self.session.get(ModerationSettings, chat_id)
        if settings is None:
            raise ValueError(f"Нет настроек модерации чата {chat_id}")

        return settings

    async def find_settings(self, chat_id: int) -> Optional[ModerationSettings]:
        return await self.session.get(ModerationSettings, chat_id)

    async def served_by(self, admin_chat_id: int) -> Optional[ModerationSettings]:
        return await self.session.scalar(
            select(ModerationSettings).where(
                ModerationSettings.admin_chat_id == admin_chat_id
            )
        )

    async def update_settings(self, chat_id: int, **values: Any) -> ModerationSettings:
        stmt = (
            insert(ModerationSettings)
            .values(chat_id=chat_id, **values)
            .on_conflict_do_update(index_elements=["chat_id"], set_=values)
            .returning(ModerationSettings)
            .execution_options(populate_existing=True)
        )

        settings = await self.session.scalar(stmt)
        if settings is None:
            raise ValueError(f"Не удалось сохранить настройки модерации чата {chat_id}")

        return settings

    async def insert_action(
        self,
        chat_id: int,
        moderator_id: int,
        target_id: int,
        action: ModerationActionType,
        duration_seconds: Optional[int],
        reason: Optional[str],
    ) -> ModerationAction:
        expires_at = None
        if duration_seconds is not None and action in TIMED_ACTIONS:
            expires_at = func.now() + timedelta(seconds=duration_seconds)
        stmt = (
            insert(ModerationAction)
            .values(
                chat_id=chat_id,
                moderator_id=moderator_id,
                target_id=target_id,
                action=action,
                duration_seconds=duration_seconds,
                reason=reason,
                expires_at=expires_at,
            )
            .returning(ModerationAction)
        )

        record = await self.session.scalar(stmt)
        if record is None:
            raise ValueError("Не удалось записать действие модерации")

        return record

    async def add_warning(
        self,
        chat_id: int,
        moderator_id: int,
        target_id: int,
        reason: Optional[str],
        expiry_seconds: Optional[int],
    ) -> None:
        # Срок считается от часов БД, как и created_at.
        expires_at = (
            None if expiry_seconds is None else func.now() + timedelta(seconds=expiry_seconds)
        )
        await self.session.execute(
            insert(ModerationWarning).values(
                chat_id=chat_id,
                moderator_id=moderator_id,
                target_id=target_id,
                reason=reason,
                expires_at=expires_at,
            )
        )

    async def active_warnings(self, chat_id: int, target_id: int) -> list[ModerationWarning]:
        stmt = (
            select(ModerationWarning)
            .where(
                ModerationWarning.chat_id == chat_id,
                ModerationWarning.target_id == target_id,
                ModerationWarning.revoked_at.is_(None),
                or_(
                    ModerationWarning.expires_at.is_(None),
                    ModerationWarning.expires_at > func.now(),
                ),
            )
            .order_by(ModerationWarning.created_at, ModerationWarning.id)
        )
        return list(await self.session.scalars(stmt))

    async def revoke_warnings(self, ids: list[int]) -> None:
        await self.session.execute(
            update(ModerationWarning)
            .where(ModerationWarning.id.in_(ids))
            .values(revoked_at=func.now())
        )

    # now() в Postgres — время начала транзакции: выборка и отметка ниже видят одно и то же
    # «сейчас», пока идут в одной сессии.
    async def due_expirations(self) -> list[DueExpiration]:
        return [*await self._due_punishments(), *await self._due_warnings()]

    async def mark_expirations_notified(self) -> None:
        await self.session.execute(
            update(ModerationAction)
            .where(
                ModerationAction.expires_at <= func.now(),
                ModerationAction.expiry_notified_at.is_(None),
            )
            .values(expiry_notified_at=func.now())
        )
        await self.session.execute(
            update(ModerationWarning)
            .where(
                ModerationWarning.revoked_at.is_(None),
                ModerationWarning.expires_at <= func.now(),
                ModerationWarning.expiry_notified_at.is_(None),
            )
            .values(expiry_notified_at=func.now())
        )

    async def _due_punishments(self) -> list[DueExpiration]:
        action = ModerationAction
        later = aliased(ModerationAction)
        # Размут, новый мут, разбан или кик после наказания делают его срок неважным.
        superseded = exists().where(
            later.chat_id == action.chat_id,
            later.target_id == action.target_id,
            later.id > action.id,
            or_(
                and_(
                    action.action == ModerationActionType.MUTE,
                    later.action.in_([ModerationActionType.MUTE, ModerationActionType.UNMUTE]),
                ),
                and_(
                    action.action == ModerationActionType.BAN,
                    later.action.in_(
                        [
                            ModerationActionType.BAN,
                            ModerationActionType.UNBAN,
                            ModerationActionType.KICK,
                        ]
                    ),
                ),
            ),
        )
        stmt = (
            select(
                action.action,
                action.chat_id,
                action.target_id,
                User.first_name,
                Chat.title,
                ModerationSettings.voice,
                ModerationSettings.admin_chat_id,
            )
            .outerjoin(User, User.telegram_id == action.target_id)
            .outerjoin(Chat, Chat.telegram_id == action.chat_id)
            .outerjoin(ModerationSettings, ModerationSettings.chat_id == action.chat_id)
            .where(
                action.expires_at <= func.now(),
                action.expiry_notified_at.is_(None),
                ~superseded,
                func.coalesce(ModerationSettings.notices_enabled, True),
            )
            .order_by(action.expires_at)
        )
        rows = await self.session.execute(stmt)
        return [
            DueExpiration(
                kind=kind,
                chat_id=chat_id,
                target_id=target_id,
                first_name=first_name,
                chat_title=title,
                voice=voice or ModerationVoice.NEUTRAL,
                admin_chat_id=admin_chat_id,
            )
            for kind, chat_id, target_id, first_name, title, voice, admin_chat_id in rows
        ]

    async def _due_warnings(self) -> list[DueExpiration]:
        warning = ModerationWarning
        active = aliased(ModerationWarning)
        left = (
            select(func.count())
            .where(
                active.chat_id == warning.chat_id,
                active.target_id == warning.target_id,
                active.revoked_at.is_(None),
                or_(active.expires_at.is_(None), active.expires_at > func.now()),
            )
            .scalar_subquery()
        )
        stmt = (
            select(
                warning.chat_id,
                warning.target_id,
                left,
                User.first_name,
                Chat.title,
                ModerationSettings.voice,
                ModerationSettings.admin_chat_id,
                ModerationSettings.warn_limit,
            )
            .outerjoin(User, User.telegram_id == warning.target_id)
            .outerjoin(Chat, Chat.telegram_id == warning.chat_id)
            .outerjoin(ModerationSettings, ModerationSettings.chat_id == warning.chat_id)
            .where(
                warning.revoked_at.is_(None),
                warning.expires_at <= func.now(),
                warning.expiry_notified_at.is_(None),
                func.coalesce(ModerationSettings.notices_enabled, True),
            )
            # Несколько варнов одного человека, сгоревших за один тик, — одно объявление.
            .group_by(
                warning.chat_id,
                warning.target_id,
                User.first_name,
                Chat.title,
                ModerationSettings.voice,
                ModerationSettings.admin_chat_id,
                ModerationSettings.warn_limit,
            )
        )
        rows = await self.session.execute(stmt)
        return [
            DueExpiration(
                kind=ModerationActionType.WARN,
                chat_id=chat_id,
                target_id=target_id,
                first_name=first_name,
                chat_title=title,
                voice=voice or ModerationVoice.NEUTRAL,
                admin_chat_id=admin_chat_id,
                warns_left=warns_left,
                warn_limit=warn_limit or 0,
            )
            for chat_id, target_id, warns_left, first_name, title, voice, admin_chat_id, warn_limit in rows
        ]
