from typing import Any

from aiogram.filters import Filter
from aiogram.types import Message
from dependency_injector.wiring import Provide

from src.bot.containers import Container
from src.bot.services import WordleService


class WordleGameFilter(Filter):
    async def __call__(
        self,
        message: Message,
        wordle_service: WordleService = Provide[Container.wordle_service],
    ) -> bool | dict[str, Any]:
        if not message.text:
            return False

        if len(message.text.split()) > 1:
            return False

        if len(message.text.split()[0]) != 5:
            return False

        if not message.from_user:
            return False

        state = wordle_service.has_active_game(message.from_user.id)

        if not state:
            return False

        return True


__all__ = ["WordleGameFilter"]
