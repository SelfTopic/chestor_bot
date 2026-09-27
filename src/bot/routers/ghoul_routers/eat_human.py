import random

from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.dialogs import Dialogs
from src.bot.game_configs import EAT_HUMAN_CONFIG
from src.bot.types import MediaDownloadType

from ...context import AppContext
from ...services.media_paths import random_media
from ..types import TextUserMessage
from .mob_battle import answer_mob_battle, rewards_text

COOLDOWN_NAME = "EAT_HUMAN"


class EatHumanHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("сожрать человека", ignore_case=True) & HasUser()

    async def survive_ambush(self) -> bool:
        ctx = self.ctx
        message = ctx.message

        battle = await ctx.battle_service.fight_mob(
            await ctx.db_user(),
            await ctx.db_ghoul(),
            is_forced=True,
            reward_log="mob ambush during eat_human reward",
        )

        await message.reply(ctx.text(Dialogs.eat_human.ambush.started()))
        await answer_mob_battle(
            ctx, message, battle, what="mob ambush during eat_human"
        )

        ambush = Dialogs.eat_human.ambush
        if battle.report.winner == "a":
            rewards = rewards_text(ctx, battle)
            await message.answer(ctx.text(ambush.won(rewards=rewards)))
            return True

        await message.answer(
            ctx.text(ambush.lost() if battle.report.winner == "b" else ambush.draw())
        )
        return False

    async def handle(self) -> None:
        ctx = self.ctx
        message = ctx.message
        telegram_id = message.user.id

        remaining = await ctx.cooldown_remaining(telegram_id, COOLDOWN_NAME)
        if remaining is not None:
            await message.reply(
                ctx.text(
                    Dialogs.eat_human.cooldown(
                        hours=remaining.total_hours,
                        minutes=remaining.minutes_remaining,
                        seconds=remaining.seconds_remaining,
                    )
                )
            )
            return

        rolled_ambush = random.random() * 100 < EAT_HUMAN_CONFIG.ambush_chance_percent
        ambushed = rolled_ambush and (
            await ctx.battle_record_service.try_claim_mob_fight(telegram_id)
        )

        if ambushed:
            survived = await self.survive_ambush()
            # Кулдаун расходуется при любом исходе.
            await ctx.cooldown_service.set_cooldown(telegram_id, COOLDOWN_NAME)
            if not survived:
                return

        ghoul, restored = await ctx.ghoul_service.eat_human(telegram_id=telegram_id)

        if not ambushed:
            await ctx.cooldown_service.set_cooldown(telegram_id, COOLDOWN_NAME)

        caption = ctx.text(
            Dialogs.eat_human.done(
                restored=restored, hunger=ghoul.hunger, count=ghoul.eat_humans
            )
        )

        media = await random_media(
            ctx.media_repository, MediaDownloadType.ANIMATION, "eat human", telegram_id
        )
        if media is None:
            await message.reply(caption)
            return

        await ctx.reply_gif(media, caption=caption)


class EatHumanRouter(BaseRouter[AppContext]):
    handlers = (EatHumanHandler,)
