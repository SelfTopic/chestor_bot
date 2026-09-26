from typing import TypeVar

from selfrot import CommandArgs
from selfrot.filter import AnyCommand, Command

TArgs = TypeVar("TArgs", bound=CommandArgs)


def transfer_command(args: type[TArgs]) -> AnyCommand[TArgs]:
    return AnyCommand(
        Command("transfer", args, ignore_case=True),
        Command("перевести", args, prefixes="", ignore_case=True),
        Command("подать", args, prefixes="", ignore_case=True),
        Command("кинуть", args, prefixes="", ignore_case=True),
    )
