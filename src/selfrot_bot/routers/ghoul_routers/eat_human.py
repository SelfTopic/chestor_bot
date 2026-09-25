"""
"сожрать человека" (BATTLE_DESIGN.md, фазы 3a+3b):
- 3a: восстановление голода раз в кулдаун (EAT_HUMAN), гифка из "eat human";
- 3b: перед едой с шансом EAT_HUMAN_CONFIG.ambush_chance_percent нападает
  моб-гуль, тоже претендующий на человека. Бой принудительный (is_forced в
  истории), общий с "бить моба" (mob_battle.py). Победа: человек доедается как в
  3a; поражение или ничья: голод не восстанавливается, но кулдаун расходуется.

Если ActiveBattle-лок уже занят (идёт дуэль), засады просто не случается, а не
отказ в еде. Как у прода, засада не проверяет боеготовность: нападают и на гуля
с 1 HP.
"""

import random

from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.game_configs import EAT_HUMAN_CONFIG
from src.bot.types import MediaDownloadType

from ...context import AppContext
from ...services.media_paths import random_media
from ...types import TextUserMessage
from .mob_battle import answer_mob_battle, run_mob_battle

COOLDOWN_NAME = "EAT_HUMAN"


class EatHumanHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("сожрать человека", ignore_case=True) & HasUser()

    ambush_text = (
        "🐺 Пока ты подкрадывался к добыче, из темноты выскочил другой "
        "гуль, тоже претендующий на человека - придётся драться!"
    )

    async def survive_ambush(self) -> bool:
        """Бой за человека (лок уже взят). True — победа, можно доедать."""
        ctx = self.ctx
        message = ctx.message

        battle = await run_mob_battle(
            ctx,
            await ctx.db_user(),
            await ctx.db_ghoul(),
            is_forced=True,
            reward_log="mob ambush during eat_human reward",
        )

        await message.reply(self.ambush_text)
        await answer_mob_battle(
            ctx, message, battle, what="mob ambush during eat_human"
        )

        if battle.winner == "a":
            await message.answer(
                battle.rewards_text() + "\n\n🍽 Соперник повержен - человек твой."
            )
            return True

        if battle.winner == "b":
            await message.answer("Моб оказался сильнее - человек достался ему.")
        else:
            await message.answer("Ничья - в суматохе добыча сбежала, поесть не вышло.")

        return False

    async def handle(self) -> None:
        ctx = self.ctx
        message = ctx.message
        telegram_id = message.user.id

        remaining = await ctx.cooldown_remaining(telegram_id, COOLDOWN_NAME)
        if remaining is not None:
            await message.reply(
                ctx.dialog_service.text(
                    key="eat_human_cooldown_error",
                    hours=remaining.total_hours,
                    minutes=remaining.minutes_remaining,
                    seconds=remaining.seconds_remaining,
                )
            )
            return

        rolled_ambush = random.random() * 100 < EAT_HUMAN_CONFIG.ambush_chance_percent
        ambushed = rolled_ambush and (
            await ctx.battle_record_service.try_claim_mob_fight(telegram_id)
        )

        if ambushed:
            survived = await self.survive_ambush()
            # Кулдаун расходуется при любом исходе: попытка поесть уже была.
            await ctx.cooldown_service.set_cooldown(telegram_id, COOLDOWN_NAME)
            if not survived:
                return

        ghoul, restored = await ctx.ghoul_service.eat_human(telegram_id=telegram_id)

        if not ambushed:
            await ctx.cooldown_service.set_cooldown(telegram_id, COOLDOWN_NAME)

        caption = ctx.dialog_service.text(
            key="eat_human_accept",
            restored=restored,
            hunger=ghoul.hunger,
            count=ghoul.eat_humans,
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
