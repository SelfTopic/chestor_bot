from typing import Any, TypeVar

from selfrot import BaseContext, CommandArgs
from selfrot.filter import AnyCommand, Command

CHAT_WORDS = ("чат", "chat")

TArgs = TypeVar("TArgs", bound=CommandArgs)


# «топ щелк чат 10» подходит и под «топ щелк» с числом «чат», поэтому варианты с чатом первые.
def chat_scoped(names: tuple[str, ...], args: type[TArgs]) -> AnyCommand[TArgs]:
    scoped = (
        Command(f"{name} {word}", args, prefixes="", ignore_case=True)
        for name in names
        for word in CHAT_WORDS
    )
    plain = (Command(name, args, prefixes="", ignore_case=True) for name in names)
    return AnyCommand(*scoped, *plain)


def wants_chat(cmd: AnyCommand[Any], ctx: BaseContext[Any]) -> bool:
    return cmd.find(ctx).name.rsplit(" ", 1)[-1] in CHAT_WORDS


def is_group(chat_type: str) -> bool:
    return chat_type in ("group", "supergroup")
