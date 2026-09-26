"""
"пить кофе": маленькая cooldown-команда, отдельная от "щёлк"/"голода", не даёт
обходить их лимит бесконечным кликаньем (COFFEE_CONFIG.snap_limit). Переиспользует
CoffeeService.execute()/execute_cooldown() как есть — чистая логика с БД, включая
day-cap рефанд при повторном клике во время кулдауна (execute_cooldown сам и
проверяет, и ставит кулдаун). Лимит щелчков и ответ с гифкой — здесь, через
ctx.db_ghoul() и ctx.reply_gif (context.py). Кулдаун — не через ctx.cooldown_remaining (тот
только читает по имени кулдауна, а execute_cooldown сам решает COFFEE это или
COFFEE_DAY и сразу отдаёт нужную запись).
"""

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

        # GhoulMiddleware уже гарантировал, что гуль есть и жив — db_ghoul() здесь
        # не «проверка на всякий случай», а то же утверждение, что у db_user().
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
