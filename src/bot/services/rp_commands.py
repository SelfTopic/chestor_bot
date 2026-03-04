import asyncio
import logging
from collections import defaultdict
from typing import Callable

from src.bot.exceptions import RpCommandError
from src.bot.types.rp_commands import RpCommandDTO, TypeRpCommandEnum
from src.database.models import Rp

from ..repositories.rp_commands import RpCommandsRepository

logger = logging.getLogger(__name__)


class RpCommandsService:
    def __init__(
        self, rp_commands_repository_factory: Callable[[], RpCommandsRepository]
    ):
        self.rp_commands_repository = rp_commands_repository_factory()
        self.cache: dict[int, dict[str, RpCommandDTO]] = {}
        self._locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    def _normalize_command(self, command: str) -> str:
        return command.strip().lower()

    async def _load_cache(self, chat_id: int) -> None:
        rp_commands = await self.rp_commands_repository.get_by_chat_id(chat_id)
        self.cache[chat_id] = {
            self._normalize_command(rp.command): RpCommandDTO(**rp.to_kwargs())
            for rp in rp_commands
        }
        logger.debug(
            "Cache loaded for chat_id=%d, %d commands", chat_id, len(rp_commands)
        )

    async def _ensure_cache(self, chat_id: int) -> None:
        if chat_id in self.cache:
            return
        async with self._locks[chat_id]:
            if chat_id not in self.cache:
                await self._load_cache(chat_id)

    async def get(self, chat_id: int, command: str) -> RpCommandDTO | None:
        command = self._normalize_command(command)
        await self._ensure_cache(chat_id)
        return self.cache.get(chat_id, {}).get(command)

    async def get_all(self, chat_id: int) -> list[RpCommandDTO]:
        await self._ensure_cache(chat_id)
        return list(self.cache.get(chat_id, {}).values())

    async def insert(
        self,
        chat_id: int,
        command: str,
        action: str,
        type_command: TypeRpCommandEnum,
        file_id: str | None = None,
    ) -> Rp:
        command = self._normalize_command(command)
        await self._ensure_cache(chat_id)

        if len(self.cache.get(chat_id, {})) >= 20 and command not in self.cache.get(
            chat_id, {}
        ):
            raise ValueError("RP command limit reached (20)")

        rp = await self.rp_commands_repository.insert(
            chat_id=chat_id,
            command=command,
            action=action,
            type_command=type_command,
            file_id=file_id,
        )

        dto = RpCommandDTO(**rp.to_kwargs())
        self.cache.setdefault(chat_id, {})[command] = dto

        logger.debug("Upserted rp command '%s' for chat_id=%d", command, chat_id)
        return rp

    async def delete(self, chat_id: int, command: str) -> None:
        command = self._normalize_command(command)
        await self._ensure_cache(chat_id)

        if command not in self.cache.get(chat_id, {}):
            raise RpCommandError("Такой Role-Play команды не существует")

        await self.rp_commands_repository.delete_by_chat_id_and_command(
            chat_id, command
        )
        self.cache[chat_id].pop(command, None)

        logger.debug("Deleted rp command '%s' for chat_id=%d", command, chat_id)

    async def delete_all(self, chat_id: int) -> None:
        await self.rp_commands_repository.delete_by_chat_id(chat_id)
        self.cache.pop(chat_id, None)
        logger.debug("Deleted all rp commands for chat_id=%d", chat_id)
