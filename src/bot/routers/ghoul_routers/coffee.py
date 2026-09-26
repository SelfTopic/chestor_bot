import time

from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.game_configs import COFFEE_CONFIG
from src.bot.types import MediaDownloadType
from src.bot.utils import parse_seconds

from ...context import AppContext
from ...services.media_paths import random_media
from ..types import TextUserMessage


class CoffeeHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("пить кофе", ignore_case=True) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        telegram_id = ctx.message.user.id

        ghoul = await ctx.db_ghoul()

        if ghoul.snap_count < COFFEE_CONFIG.snap_limit:
            await ctx.message.reply(
                text=ctx.dialog_service.text(key="coffee_snap_limit")
            )
            return

        cooldown = await ctx.coffee_service.execute_cooldown(telegram_id)
        if cooldown is not None:
            remaining = parse_seconds(int(cooldown.end_at - time.time()))
            await ctx.message.reply(
                text=ctx.dialog_service.text(
                    key="coffee_cooldown_error",
                    hours=remaining.total_hours,
                    minutes=remaining.minutes_remaining,
                    seconds=remaining.seconds_remaining,
                )
            )
            return

        result = await ctx.coffee_service.execute(telegram_id)
        text = ctx.dialog_service.text(
            key="coffee_accept", count=result.ghoul.coffee_count, money=result.award
        )

        media = await random_media(
            ctx.media_repository, MediaDownloadType.ANIMATION, "coffee", telegram_id
        )
        if media is None:
            await ctx.message.reply(text=text)
            return

        await ctx.reply_gif(media, caption=text)


class CoffeeRouter(BaseRouter[AppContext]):
    handlers = (CoffeeHandler,)
