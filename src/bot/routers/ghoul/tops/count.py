from typing import Any

from pydantic import Field
from selfrot import CommandArgs, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import AnyCommand

from src.bot.dialogs import Dialogs, Line

from ....context import AppContext
from ...chat_scope import chat_scoped, is_group, wants_chat


class GhoulTopArgs(CommandArgs):
    count: int = Field(20, ge=0)
    extra: Rest = ""


def top_command(*names: str) -> AnyCommand[GhoulTopArgs]:
    return chat_scoped(names, GhoulTopArgs)


def top_row(ctx: AppContext[Any], place: int, name: str | None, value: object) -> str:
    name = name or ctx.text(Dialogs.tops.unknown_name())
    return ctx.text(Dialogs.tops.row(place=place, name=name, value=value))


def top_title(ctx: AppContext[Any], title: Line, chat_id: int | None) -> str:
    text = ctx.text(title)
    return text if chat_id is None else ctx.text(Dialogs.tops.in_chat(title=text))


def top_text(ctx: AppContext[Any], title: str, rows: list[str]) -> str:
    body = "\n".join(rows) if rows else ctx.text(Dialogs.tops.empty())
    return ctx.text(Dialogs.tops.list(title=title, rows=body))


class GhoulTopHandler:
    cmd: AnyCommand[GhoulTopArgs]
    ctx: AppContext[Any]
    not_a_number = Dialogs.tops.not_a_number()
    out_of_range = Dialogs.tops.out_of_range()
    chat_only_group = Dialogs.tops.chat_only_group()

    async def handle(self) -> None:
        count = self.cmd.parse(self.ctx).count
        if not 1 <= count <= 50:
            await self.ctx.say(self.out_of_range)
            return
        chat = self.ctx.chat
        assert chat is not None
        if not wants_chat(self.cmd, self.ctx):
            await self.show(count, None)
        elif is_group(chat.type):
            await self.show(count, chat.id)
        else:
            await self.ctx.say(self.chat_only_group, reply=True)

    async def show(self, count: int, chat_id: int | None) -> None:
        raise NotImplementedError

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.say(self.not_a_number)
            return
        raise exc
