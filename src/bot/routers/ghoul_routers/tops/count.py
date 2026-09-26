from typing import Any

from pydantic import Field
from selfrot import CommandArgs, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from ....context import AppContext


class GhoulTopArgs(CommandArgs):
    count: int = Field(20, ge=0)
    extra: Rest = ""


def top_command(name: str) -> Command[GhoulTopArgs]:
    return Command(name, GhoulTopArgs, prefixes="", ignore_case=True)


class GhoulTopHandler:
    cmd: Command[GhoulTopArgs]
    ctx: AppContext[Any]
    not_a_number = "Топ нужно указывать положительной цифрой"
    out_of_range = "Топ не может выходить за пределы значений 1-50"

    async def handle(self) -> None:
        count = self.cmd.parse(self.ctx).count
        if not 1 <= count <= 50:
            await self.ctx.message.answer(self.out_of_range)
            return
        await self.show(count)

    async def show(self, count: int) -> None:
        raise NotImplementedError

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.answer(self.not_a_number)
            return
        raise exc
