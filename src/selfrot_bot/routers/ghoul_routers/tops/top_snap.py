"""
"топ щелк [N]": топ по количеству "щелчков". TextStartswith — как и у прод-Text(...,
startswith=True) — совпадает и с "топ щелкает" (нет проверки границы слова);
message.text.split()[2] тогда падает IndexError. Известная особенность, оставлена
как есть (см. журнал порта: обсуждали с пользователем, чинить не сейчас).
"""

from selfrot import BaseRouter, MessageHandler
from selfrot.filter import TextStartswith
from selfrot.types import TextMessage

from ....context import AppContext

_PREFIX = "топ щелк"


class TopSnapHandler(MessageHandler[AppContext[TextMessage]]):
    query = TextStartswith(_PREFIX, ignore_case=True)

    async def handle(self) -> None:
        ctx = self.ctx
        text = ctx.message.text
        count = 20

        if text.lower() != _PREFIX:
            count_str = text.split()[2]
            if not count_str.isdigit():
                await ctx.message.answer("Топ нужно указывать положительной цифрой")
                return
            count = int(count_str)

        if count < 1 or count > 50:
            await ctx.message.answer("Топ не может выходить за пределы значений 1-50")
            return

        top = await ctx.ghoul_service.get_top_snap(count)
        if not top:
            await ctx.message.answer("А нету топа прикинь нахуй.")
            return

        answer_text = f"Топ {count} самых сломанных пальцев\n\n"
        for place, ghoul in enumerate(top, start=1):
            user = await ctx.user_service.get(find_by=ghoul.telegram_id)
            name = user.first_name if user is not None else "Unknown"
            answer_text += f"{place}. {name} - {ghoul.snap_count}\n"

        await ctx.message.answer(answer_text)


class TopSnapRouter(BaseRouter[AppContext]):
    handlers = (TopSnapHandler,)
