from typing import Any

from selfrot import BaseContext
from selfrot.filter import BaseFilter

from src.bot.dialogs import BASE_LANGUAGE, Line

from ..context import AppContext


class InLanguage(BaseFilter[AppContext[Any]]):
    def __init__(self, language: str) -> None:
        self.language = language

    async def check(self, ctx: BaseContext[Any]) -> bool:
        assert isinstance(ctx, AppContext)
        return ctx.language == self.language


# Цитаты, серии и слова Wordle есть только на русском.
RUSSIAN_ONLY = InLanguage(BASE_LANGUAGE)


class NotInLanguageReply:
    ctx: AppContext[Any]
    line: Line

    async def handle(self) -> None:
        await self.ctx.say(self.line, reply=True)
