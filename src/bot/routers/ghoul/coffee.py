import time

from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.dialogs import Dialogs
from src.bot.game_configs import COFFEE_CONFIG
from src.bot.utils import parse_seconds

from ...context import AppContext
from ..types import TextUserMessage


class CoffeeHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("пить кофе", ignore_case=True) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        telegram_id = ctx.message.user.id

        ghoul = await ctx.db_ghoul()

        if ghoul.snap_count < COFFEE_CONFIG.snap_limit:
            await ctx.say(Dialogs.coffee.snap_limit(), reply=True)
            return

        cooldown = await ctx.coffee_service.execute_cooldown(telegram_id)
        if cooldown is not None:
            remaining = parse_seconds(int(cooldown.end_at - time.time()))
            await ctx.say(
                Dialogs.coffee.cooldown(
                    hours=remaining.total_hours,
                    minutes=remaining.minutes_remaining,
                    seconds=remaining.seconds_remaining,
                ),
                reply=True,
            )
            return

        result = await ctx.coffee_service.execute(telegram_id)
        done = Dialogs.coffee.done(count=result.ghoul.coffee_count, money=result.award)
        await ctx.say(done, reply=True)


class CoffeeRouter(BaseRouter[AppContext]):
    handlers = (CoffeeHandler,)
