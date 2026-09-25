import logging
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from selfrot import BaseContext, CommandArgs
from selfrot.exceptions import DefinitionError
from selfrot.filter import BaseFilter, Command
from selfrot.types import Message

from src.bot.types.rp_commands import RpCommandDTO

from ....context import AppContext
from ....types import CaptionMessage, TextMessage

logger = logging.getLogger(__name__)


TArgs = TypeVar("TArgs", bound=CommandArgs)


@dataclass(frozen=True)
class RpMatch(Generic[TArgs]):
    """Что нашёл фильтр: команда чата и тот же Command, которым она распознана."""

    rp: RpCommandDTO
    command: Command[TArgs]  # аргументы берут им: command.parse(ctx)


class RpCommandFilter(BaseFilter[AppContext[Any]], Generic[TArgs]):
    """
    Сообщение начинается с Role-Play команды этого чата. Имена команд лежат в БД, а
    Command принимает имя при создании, поэтому Command собирается на лету, по одному
    на команду чата: фильтр и разбор аргументов в хендлере пользуются одним и тем же.
    args задаёт форму аргументов (она описана рядом с хендлером). Найденное фильтр не
    хранит (query один на класс, апдейты идут параллельно): хендлер берёт его явно
    через find(ctx).
    """

    guarantees = TextMessage

    def __init__(self, args: type[TArgs]) -> None:
        self.args = args

    def _command(self, rp: RpCommandDTO) -> Command[TArgs] | None:
        try:
            return Command(rp.command, self.args, prefixes="", ignore_case=True)
        except DefinitionError:
            # имя, которое Command не принимает (пустое): такую команду не ищем
            logger.warning("Role-Play команда %r не подходит для Command", rp.command)
            return None

    async def find(self, ctx: BaseContext[Any]) -> RpMatch[TArgs] | None:
        assert isinstance(ctx, AppContext)

        message = ctx.event
        if not isinstance(message, Message) or not message.text:
            return None

        for rp in await ctx.rp_commands_service.get_all(message.chat.id):
            command = self._command(rp)
            if command is not None and await command.check(ctx):
                return RpMatch(rp, command)

        return None

    async def check(self, ctx: BaseContext[Any]) -> bool:
        return await self.find(ctx) is not None


class SetRpOnMedia(BaseFilter[AppContext[Any]]):
    """Фото или гифка с подписью `/set_rp ...`. Слов мало — хендлер подскажет формат."""

    guarantees = CaptionMessage

    async def check(self, ctx: BaseContext[Any]) -> bool:
        message = ctx.event
        if not isinstance(message, Message) or not message.caption:
            return False

        if not message.photo and not message.animation:
            return False

        return message.caption.lower().split()[0] == "/set_rp"
