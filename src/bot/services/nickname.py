import re

from ...database.models import NICKNAME_MAX_LENGTH
from ..exceptions import NicknameProblem, NicknameRejected
from ..repositories.nickname import NicknameRepository

# @username и ссылки в нике превращали бы каждое упоминание игрока в рекламу.
LINK = re.compile(r"@|https?://|www\.|t\.me/|\w\.(?:ru|com|me|org|net|io)\b", re.IGNORECASE)


class NicknameService:
    def __init__(self, repository: NicknameRepository) -> None:
        self._repository = repository

    async def in_chat(self, chat_id: int) -> dict[int, str]:
        return await self._repository.in_chat(chat_id)

    async def set(self, chat_id: int, telegram_id: int, raw: str) -> str:
        nickname = " ".join(raw.split())
        if not nickname:
            raise NicknameRejected(NicknameProblem.EMPTY)
        if len(nickname) > NICKNAME_MAX_LENGTH:
            raise NicknameRejected(NicknameProblem.TOO_LONG)
        if LINK.search(nickname):
            raise NicknameRejected(NicknameProblem.LINK)

        await self._repository.set(chat_id, telegram_id, nickname)
        return nickname

    async def clear(self, chat_id: int, telegram_id: int) -> str | None:
        return await self._repository.delete(chat_id, telegram_id)
