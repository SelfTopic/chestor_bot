from datetime import timedelta
from typing import Any, Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import ModerationAction, ModerationSettings, ModerationWarning
from ..types import ModerationActionType
from .base import Base


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
        stmt = (
            insert(ModerationAction)
            .values(
                chat_id=chat_id,
                moderator_id=moderator_id,
                target_id=target_id,
                action=action,
                duration_seconds=duration_seconds,
                reason=reason,
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
