import logging
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from selfrot import BaseContext, CommandArgs
from selfrot.exceptions import DefinitionError
from selfrot.filter import BaseFilter, Command
from selfrot.types import Message

from src.bot.types.rp_commands import RpCommandDTO

from ....context import AppContext
from ...types import CaptionMessage, TextMessage

logger = logging.getLogger(__name__)


TArgs = TypeVar("TArgs", bound=CommandArgs)


@dataclass(frozen=True)
class RpMatch(Generic[TArgs]):
    rp: RpCommandDTO
    command: Command[TArgs]


class RpCommandFilter(BaseFilter[AppContext[Any]], Generic[TArgs]):
    guarantees = TextMessage

    def __init__(self, args: type[TArgs]) -> None:
        self.args = args

    def _command(self, rp: RpCommandDTO) -> Command[TArgs] | None:
        try:
            return Command(rp.command, self.args, prefixes="", ignore_case=True)
        except DefinitionError:
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
    guarantees = CaptionMessage

    async def check(self, ctx: BaseContext[Any]) -> bool:
        message = ctx.event
        if not isinstance(message, Message) or not message.caption:
            return False

        if not message.photo and not message.animation:
            return False

        return message.caption.lower().split()[0] == "/set_rp"
