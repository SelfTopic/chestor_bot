from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.dialogs import Dialogs
from src.bot.game_configs import SNAP_CONFIG

from ...context import AppContext
from ..types import TextUserMessage


class SnapHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = (
        Text("щелк", ignore_case=True) | Text("щёлк", ignore_case=True)
    ) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        telegram_id = ctx.message.user.id

        remaining = await ctx.cooldown_remaining(telegram_id, "SNAP")
        if remaining is not None:
            await ctx.say(
                Dialogs.snap.cooldown(
                    minutes=str(remaining.minutes_remaining),
                    seconds=str(remaining.seconds_remaining),
                ),
                reply=True,
            )
            return

        new_ghoul = await ctx.ghoul_service.snap_finger(telegram_id)
        award = SNAP_CONFIG.award

        await ctx.user_service.plus_balance(
            telegram_id=telegram_id, change_balance=award, log="snap finger award"
        )
        await ctx.cooldown_service.set_cooldown(telegram_id, "SNAP")

        done = Dialogs.snap.done(count=str(new_ghoul.snap_count), money=str(award))
        await ctx.say(done, reply=True)


class SnapRouter(BaseRouter[AppContext]):
    handlers = (SnapHandler,)
