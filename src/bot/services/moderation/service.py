from typing import Optional

from src.database.models import ModerationAction, ModerationSettings

from ...repositories import ModerationRepository
from ...types import ModerationActionType


class ModerationService:
    def __init__(self, moderation_repository: ModerationRepository) -> None:
        self.moderation_repository = moderation_repository

    async def settings(self, chat_id: int) -> ModerationSettings:
        return await self.moderation_repository.settings(chat_id)

    async def record(
        self,
        chat_id: int,
        moderator_id: int,
        target_id: int,
        action: ModerationActionType,
        *,
        duration_seconds: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> ModerationAction:
        return await self.moderation_repository.insert_action(
            chat_id=chat_id,
            moderator_id=moderator_id,
            target_id=target_id,
            action=action,
            duration_seconds=duration_seconds,
            reason=reason,
        )
