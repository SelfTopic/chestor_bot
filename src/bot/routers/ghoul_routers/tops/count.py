from typing import Any

from pydantic import Field
from selfrot import CommandArgs, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from src.bot.dialogs import Dialogs

from ....context import AppContext


class GhoulTopArgs(CommandArgs):
    count: int = Field(20, ge=0)
    extra: Rest = ""


def top_command(name: str) -> Command[GhoulTopArgs]:
    return Command(name, GhoulTopArgs, prefixes="", ignore_case=True)


def top_row(ctx: AppContext[Any], place: int, name: str | None, value: object) -> str:
    name = name or ctx.text(Dialogs.tops.unknown_name())
    return ctx.text(Dialogs.tops.row(place=place, name=name, value=value))


def top_text(ctx: AppContext[Any], title: str, rows: list[str]) -> str:
    body = "\n".join(rows) if rows else ctx.text(Dialogs.tops.empty())
    return ctx.text(Dialogs.tops.list(title=title, rows=body))


class GhoulTopHandler:
    cmd: Command[GhoulTopArgs]
    ctx: AppContext[Any]
    not_a_number = Dialogs.tops.not_a_number()
    out_of_range = Dialogs.tops.out_of_range()

    async def handle(self) -> None:
        count = self.cmd.parse(self.ctx).count
        if not 1 <= count <= 50:
            await self.ctx.message.answer(self.ctx.text(self.out_of_range))
            return
        await self.show(count)

    async def show(self, count: int) -> None:
        raise NotImplementedError

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.answer(self.ctx.text(self.not_a_number))
            return
        raise exc
