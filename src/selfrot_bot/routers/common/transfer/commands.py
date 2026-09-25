from typing import TypeVar

from selfrot import CommandArgs
from selfrot.filter import AnyCommand, Command

TArgs = TypeVar("TArgs", bound=CommandArgs)


def transfer_command(args: type[TArgs]) -> AnyCommand[TArgs]:
    """
    Одна команда под четырьмя именами: /transfer, перевести, подать, кинуть. У прода
    для этого было `Text("подать", startswith=True)`, которое цепляло и «податься».
    Сама AnyCommand это фильтр (идёт в query), parse(ctx) отдаёт аргументы по той форме,
    какой бы из четырёх команда ни позвали.
    """
    return AnyCommand(
        Command("transfer", args, ignore_case=True),
        Command("перевести", args, prefixes="", ignore_case=True),
        Command("подать", args, prefixes="", ignore_case=True),
        Command("кинуть", args, prefixes="", ignore_case=True),
    )
