"""
"топ щелк [N]": топ по количеству "щелчков". N разбирает GhoulTopHandler (count.py).

Исправленный прод-баг: прод ловил команду по началу текста и падал IndexError на
"топ щелкает" (split()[2] там нет). Здесь это команда "топ щелк" целиком.
"""

from selfrot import BaseRouter, MessageHandler
from selfrot.types import TextMessage

from ....context import AppContext
from .count import GhoulTopHandler, top_command


class TopSnapHandler(GhoulTopHandler, MessageHandler[AppContext[TextMessage]]):
    cmd = top_command("топ щелк")
    query = cmd

    async def show(self, count: int) -> None:
        ctx = self.ctx
        top = await ctx.ghoul_service.get_top_snap(count)
        if not top:
            await ctx.message.answer("А нету топа прикинь нахуй.")
            return

        names = await ctx.first_names([ghoul.telegram_id for ghoul in top])
        answer_text = f"Топ {count} самых сломанных пальцев\n\n"
        for place, ghoul in enumerate(top, start=1):
            name = names.get(ghoul.telegram_id, "Unknown")
            answer_text += f"{place}. {name} - {ghoul.snap_count}\n"

        await ctx.message.answer(answer_text)


class TopSnapRouter(BaseRouter[AppContext]):
    handlers = (TopSnapHandler,)
