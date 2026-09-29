from typing import Optional

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import ModerationAction, ModerationSettings
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
