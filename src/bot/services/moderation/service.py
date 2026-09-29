import re
from typing import Optional

from src.database.models import ModerationAction, ModerationSettings

from ...exceptions import (
    AdminChatIsSelf,
    AdminChatNotLinked,
    AdminChatTaken,
    DurationParseError,
    TermOutOfRange,
)
from ...repositories import ModerationRepository
from ...types import Duration, ModerationActionType, ModerationVoice, Punishment
from ..duration_parser import DurationParser

# Срок короче или длиннее Telegram молча считает вечным.
MIN_TERM_SECONDS = 30
MAX_TERM_SECONDS = 366 * 24 * 3600


class ModerationService:
    def __init__(self, moderation_repository: ModerationRepository) -> None:
        self.moderation_repository = moderation_repository

    async def settings(self, chat_id: int) -> ModerationSettings:
        return await self.moderation_repository.settings(chat_id)

    async def set_mute_default(
        self, chat_id: int, seconds: Optional[int]
    ) -> ModerationSettings:
        return await self.moderation_repository.update_settings(
            chat_id, mute_default_seconds=seconds
        )

    async def set_ban_default(
        self, chat_id: int, seconds: Optional[int]
    ) -> ModerationSettings:
        return await self.moderation_repository.update_settings(
            chat_id, ban_default_seconds=seconds
        )

    async def set_voice(
        self, chat_id: int, voice: ModerationVoice
    ) -> ModerationSettings:
        return await self.moderation_repository.update_settings(chat_id, voice=voice)

    async def admin_chat_requested(self, chat_id: int, admin_chat_id: int) -> bool:
        settings = await self.moderation_repository.find_settings(chat_id)
        return settings is not None and settings.admin_chat_request == admin_chat_id

    async def request_admin_chat(self, chat_id: int, admin_chat_id: int) -> None:
        if admin_chat_id == chat_id:
            raise AdminChatIsSelf()
        await self._ensure_free(chat_id, admin_chat_id)
        await self.moderation_repository.update_settings(
            chat_id, admin_chat_request=admin_chat_id
        )

    async def link_admin_chat(self, chat_id: int, admin_chat_id: int) -> Optional[int]:
        settings = await self.settings(chat_id)
        previous = settings.admin_chat_id
        await self._ensure_free(chat_id, admin_chat_id)
        await self.moderation_repository.update_settings(
            chat_id, admin_chat_id=admin_chat_id, admin_chat_request=None
        )
        return previous if previous != admin_chat_id else None

    async def unlink_admin_chat(self, chat_id: int) -> int:
        settings = await self.settings(chat_id)
        previous = settings.admin_chat_id
        if previous is None:
            raise AdminChatNotLinked()
        await self.moderation_repository.update_settings(
            chat_id, admin_chat_id=None, admin_chat_request=None
        )
        return previous

    async def _ensure_free(self, chat_id: int, admin_chat_id: int) -> None:
        served = await self.moderation_repository.served_by(admin_chat_id)
        if served is not None and served.chat_id != chat_id:
            raise AdminChatTaken()

    def term(self, text: str) -> Optional[int]:
        return self._seconds(DurationParser.parse_string(text))

    def punishment(self, text: str, default_seconds: Optional[int]) -> Punishment:
        words = list(re.finditer(r"\S+", text))
        for last in reversed(words):
            try:
                duration = DurationParser.parse_string(text[: last.end()])
            except DurationParseError:
                continue

            reason = text[last.end() :].strip() or None
            return Punishment(self._seconds(duration), reason)

        return Punishment(default_seconds, text.strip() or None)

    def _seconds(self, duration: Duration) -> Optional[int]:
        if duration.raw in DurationParser.FOREVER_KEYWORDS:
            return None

        seconds = duration.components.total_seconds
        if not MIN_TERM_SECONDS <= seconds <= MAX_TERM_SECONDS:
            raise TermOutOfRange(MIN_TERM_SECONDS, MAX_TERM_SECONDS)
        return seconds

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
