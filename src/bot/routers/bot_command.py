from typing import TypeVar

from selfrot import CommandArgs
from selfrot.filter import AnyCommand, Command

TArgs = TypeVar("TArgs", bound=CommandArgs)


def bot_command(action: str, args: type[TArgs]) -> AnyCommand[TArgs]:
    return AnyCommand(
        *(
            Command(
                f"{name} {action}", args, prefixes="", ignore_case=True, strict=True
            )
            for name in ("бот", "честор")
        )
    )
