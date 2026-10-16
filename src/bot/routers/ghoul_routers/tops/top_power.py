from selfrot import BaseRouter, MessageHandler
from selfrot.types import TextMessage

from src.bot.dialogs import Dialogs

from ....context import AppContext
from .count import GhoulTopHandler, top_command, top_row, top_text


class TopPowerHandler(GhoulTopHandler, MessageHandler[AppContext[TextMessage]]):
    cmd = top_command("топ бм")
    query = cmd

    async def show(self, count: int) -> None:
        ctx = self.ctx
        ghoul_service = ctx.ghoul_service
        top = await ghoul_service.get_top_power(count)
        if not top:
            await ctx.say(Dialogs.tops.empty())
            return

        names = await ctx.first_names([ghoul.telegram_id for ghoul in top])
        rows = []
        for place, ghoul in enumerate(top, start=1):
            power = ghoul_service.calculate_power(ghoul)
            rank = ghoul_service.get_danger_rank(power)
            value = ctx.text(Dialogs.tops.power_value(power=power, rank=rank))
            rows.append(top_row(ctx, place, names.get(ghoul.telegram_id), value))
        title = ctx.text(Dialogs.tops.power_title(count=count))
        await ctx.message.answer(top_text(ctx, title, rows))


class TopPowerRouter(BaseRouter[AppContext]):
    handlers = (TopPowerHandler,)
