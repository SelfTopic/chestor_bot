import re
from typing import Any

from aiogram.filters import Filter
from aiogram.types import Message


class Text(Filter):
    def __init__(
        self,
        command: str,
        lower: bool = True,
        startswith: bool = False,
        pattern: str | None = None,
    ) -> None:
        self.command = command
        self.lower = lower
        self.startswith = startswith
        self.pattern = pattern

    async def __call__(self, message: Message) -> Any:
        filtred_text = message.text

        if not filtred_text:
            return False

        if self.lower:
            filtred_text = filtred_text.lower()

        if self.pattern:
            return bool(re.match(self.pattern, filtred_text))

        if self.startswith:
            return filtred_text.startswith(self.command)

        return self.command == filtred_text


__all__ = ["Text"]
