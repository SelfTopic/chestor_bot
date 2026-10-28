from typing import TypeVar

from selfrot import CommandArgs
from selfrot.filter import AnyCommand, Command

TArgs = TypeVar("TArgs", bound=CommandArgs)


BOT_NAMES = ("бот", "честор", "bot", "chestor")


# Действие называют на любом языке бота: «бот выбери» и «bot pick» — одна команда.
def bot_command(args: type[TArgs], *actions: str) -> AnyCommand[TArgs]:
    return AnyCommand(
        *(
            Command(
                f"{name} {action}", args, prefixes="", ignore_case=True, strict=True
            )
            for action in actions
            for name in BOT_NAMES
        )
    )
