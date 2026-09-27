from selfrot import BaseRouter, MessageHandler
from selfrot.types import TextMessage

from src.bot.dialogs import Dialogs

from ....context import AppContext
from .count import GhoulTopHandler, top_command, top_row, top_text


class TopSnapHandler(GhoulTopHandler, MessageHandler[AppContext[TextMessage]]):
    cmd = top_command("топ щелк")
    query = cmd

    async def show(self, count: int) -> None:
        ctx = self.ctx
        top = await ctx.ghoul_service.get_top_snap(count)
        if not top:
            await ctx.say(Dialogs.tops.empty())
            return

        names = await ctx.first_names([ghoul.telegram_id for ghoul in top])
        rows = [
            top_row(ctx, place, names.get(ghoul.telegram_id), ghoul.snap_count)
            for place, ghoul in enumerate(top, start=1)
        ]
        title = ctx.text(Dialogs.tops.snap_title(count=count))
        await ctx.message.answer(top_text(ctx, title, rows))


class TopSnapRouter(BaseRouter[AppContext]):
    handlers = (TopSnapHandler,)
