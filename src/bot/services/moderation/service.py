import re
from typing import Optional

from src.database.models import ModerationAction, ModerationSettings

from ...exceptions import DurationParseError, TermOutOfRange
from ...repositories import ModerationRepository
from ...types import ModerationActionType, Punishment
from ..duration_parser import DurationParser

# Срок короче или длиннее Telegram молча считает вечным.
MIN_TERM_SECONDS = 30
MAX_TERM_SECONDS = 366 * 24 * 3600


class ModerationService:
    def __init__(self, moderation_repository: ModerationRepository) -> None:
        self.moderation_repository = moderation_repository

    async def settings(self, chat_id: int) -> ModerationSettings:
        return await self.moderation_repository.settings(chat_id)

    def punishment(self, text: str, default_seconds: int) -> Punishment:
        words = list(re.finditer(r"\S+", text))
        for last in reversed(words):
            try:
                duration = DurationParser.parse_string(text[: last.end()])
            except DurationParseError:
                continue

            reason = text[last.end() :].strip() or None
            if duration.raw in DurationParser.FOREVER_KEYWORDS:
                return Punishment(None, reason)

            seconds = duration.components.total_seconds
            if not MIN_TERM_SECONDS <= seconds <= MAX_TERM_SECONDS:
                raise TermOutOfRange(MIN_TERM_SECONDS, MAX_TERM_SECONDS)
            return Punishment(seconds, reason)

        return Punishment(default_seconds, text.strip() or None)

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
