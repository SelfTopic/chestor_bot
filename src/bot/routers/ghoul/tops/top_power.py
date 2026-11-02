from selfrot import BaseRouter, MessageHandler
from selfrot.types import TextMessage

from src.bot.dialogs import Dialogs
from src.database.models import Ghoul

from ....context import AppContext
from ...tops import you_line
from .count import GhoulTopHandler, top_command, top_row, top_text, top_title


class TopPowerHandler(GhoulTopHandler, MessageHandler[AppContext[TextMessage]]):
    cmd = top_command("топ бм", "top cp")
    query = cmd

    async def show(self, count: int, chat_id: int | None) -> None:
        ctx = self.ctx
        ghoul_service = ctx.ghoul_service
        top = await ghoul_service.get_top_power(count, chat_id)
        if not top:
            await ctx.say(Dialogs.tops.empty())
            return

        names = await ctx.names([ghoul.telegram_id for ghoul in top])
        rows = [
            top_row(ctx, place, names.get(ghoul.telegram_id), self.power(ghoul))
            for place, ghoul in enumerate(top, start=1)
        ]
        title = top_title(ctx, Dialogs.tops.power_title(count=count), chat_id)
        me = await ctx.db_ghoul()
        place = await ghoul_service.top_place("power", me.telegram_id, chat_id)
        you = you_line(ctx, place, self.power(me))
        await ctx.message.answer(top_text(ctx, title, rows, you))

    def power(self, ghoul: Ghoul) -> str:
        ghoul_service = self.ctx.ghoul_service
        power = ghoul_service.calculate_power(ghoul)
        rank = ghoul_service.get_danger_rank(power)
        return self.ctx.text(Dialogs.tops.power_value(power=power, rank=rank))


class TopPowerRouter(BaseRouter[AppContext]):
    handlers = (TopPowerHandler,)
