from selfrot import BaseRouter, CommandArgs, MessageHandler
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command, HasUser

from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import (
    PromoAlreadyActivated,
    PromoExhausted,
    PromoExpired,
    PromoNotFound,
)

from ...context import AppContext
from ..promo_rewards import reward_lines
from ..types import TextUserMessage


class PromoArgs(CommandArgs):
    name: str


class PromoHandler(MessageHandler[AppContext[TextUserMessage]]):
    cmd = Command("промо", PromoArgs, prefixes="", ignore_case=True)
    query = cmd & HasUser()
    usage = Dialogs.promo.usage()

    async def handle(self) -> None:
        name = self.cmd.parse(self.ctx).name
        rewards = await self.ctx.promo_service.activate(name, self.ctx.message.user.id)
        activated = Dialogs.promo.activated(name=name, rewards=reward_lines(self.ctx, rewards))
        await self.ctx.say(activated, reply=True)

    async def on_error(self, exc: Exception) -> None:
        line: Line
        match exc:
            case CommandArgsError():
                line = self.usage
            case PromoNotFound(name=name):
                line = Dialogs.promo.not_found(name=name)
            case PromoExpired(name=name):
                line = Dialogs.promo.expired(name=name)
            case PromoExhausted(name=name):
                line = Dialogs.promo.exhausted(name=name)
            case PromoAlreadyActivated(name=name):
                line = Dialogs.promo.already(name=name)
            case _:
                raise exc
        await self.ctx.say(line, reply=True)


class PromoRouter(BaseRouter[AppContext]):
    handlers = (PromoHandler,)
