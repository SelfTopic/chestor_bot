"""
"щелк"/"щёлк": простая cooldown-команда — награда + гиф, два разных слова (не
регистр — "ё" не сводится к "е" через ignore_case). Использует оба общих ctx-хелпера
(cooldown_remaining/reply_gif, context.py) — никакой своей логики кулдауна/гифки.
"""

from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.game_configs import SNAP_CONFIG
from src.bot.types import MediaDownloadType

from ...context import AppContext
from ...services.media_paths import random_media
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
            await ctx.message.reply(
                text=ctx.dialog_service.text(
                    key="snap_finger_cooldown_error",
                    minutes=str(remaining.minutes_remaining),
                    seconds=str(remaining.seconds_remaining),
                )
            )
            return

        new_ghoul = await ctx.ghoul_service.snap_finger(telegram_id)
        award = SNAP_CONFIG.award

        await ctx.user_service.plus_balance(
            telegram_id=telegram_id, change_balance=award, log="snap finger award"
        )
        await ctx.cooldown_service.set_cooldown(telegram_id, "SNAP")

        caption = ctx.dialog_service.text(
            key="snap_finger_accept",
            count=str(new_ghoul.snap_count),
            money=str(award),
        )

        media = await random_media(
            ctx.media_repository,
            MediaDownloadType.ANIMATION,
            "snap finger",
            telegram_id,
        )
        if media is None:
            await ctx.message.reply(text=caption)
            return

        await ctx.reply_gif(media, caption=caption)


class SnapRouter(BaseRouter[AppContext]):
    handlers = (SnapHandler,)
