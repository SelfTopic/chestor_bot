from selfrot import BaseRouter, MessageHandler
from selfrot.filter import Command, HasUser

from src.bot.dialogs import Dialogs, Line

from ...context import AppContext
from ..types import TextUserMessage


# Миксин не наследует MessageHandler: selfrot проверяет заголовок только на прямых базах.
class RateRoastHandler:
    ctx: AppContext[TextUserMessage]
    rating = 0
    done: Line = Dialogs.admin.roast.good()

    async def handle(self) -> None:
        replied = self.ctx.message.reply_to_message
        if replied is None:
            await self.ctx.say(Dialogs.admin.roast.usage(), reply=True)
            return

        rated = await self.ctx.roast_service.rate(
            self.ctx.message.chat.id, replied.message_id, self.rating
        )
        await self.ctx.say(self.done if rated else Dialogs.admin.roast.not_found(), reply=True)


class GoodRoastHandler(RateRoastHandler, MessageHandler[AppContext[TextUserMessage]]):
    query = Command("good") & HasUser()
    rating = 1
    done = Dialogs.admin.roast.good()


class BadRoastHandler(RateRoastHandler, MessageHandler[AppContext[TextUserMessage]]):
    query = Command("bad") & HasUser()
    rating = -1
    done = Dialogs.admin.roast.bad()


class RoastRatingRouter(BaseRouter[AppContext]):
    handlers = (GoodRoastHandler, BadRoastHandler)
