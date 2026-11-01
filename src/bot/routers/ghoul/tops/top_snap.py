from selfrot import BaseRouter, MessageHandler
from selfrot.types import TextMessage

from src.bot.dialogs import Dialogs

from ....context import AppContext
from ...tops import you_line
from .count import GhoulTopHandler, top_command, top_row, top_text, top_title


class TopSnapHandler(GhoulTopHandler, MessageHandler[AppContext[TextMessage]]):
    cmd = top_command("топ щелк", "top snap")
    query = cmd

    async def show(self, count: int, chat_id: int | None) -> None:
        ctx = self.ctx
        top = await ctx.ghoul_service.get_top_snap(count, chat_id)
        if not top:
            await ctx.say(Dialogs.tops.empty())
            return

        names = await ctx.first_names([ghoul.telegram_id for ghoul in top])
        rows = [
            top_row(ctx, place, names.get(ghoul.telegram_id), ghoul.snap_count)
            for place, ghoul in enumerate(top, start=1)
        ]
        title = top_title(ctx, Dialogs.tops.snap_title(count=count), chat_id)
        me = await ctx.db_ghoul()
        place = await ctx.ghoul_service.top_place("snap", me.telegram_id, chat_id)
        you = you_line(ctx, place, me.snap_count)
        await ctx.message.answer(top_text(ctx, title, rows, you))


class TopSnapRouter(BaseRouter[AppContext]):
    handlers = (TopSnapHandler,)
