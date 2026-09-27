from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.dialogs import Dialogs
from src.bot.exceptions import (
    FighterHasPendingBattleError,
    FighterIsDeadError,
    FighterNotCombatReadyError,
)

from ...context import AppContext
from ..types import TextUserMessage
from .mob_battle import answer_mob_battle, rewards_text

COOLDOWN_NAME = "MOB_FIGHT"


class MobFightHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("бить моба", ignore_case=True) & HasUser()

    busy_text = Dialogs.mob.busy()

    async def handle(self) -> None:
        ctx = self.ctx
        message = ctx.message
        telegram_id = message.user.id
        battles = ctx.battle_record_service

        user = await ctx.db_user()
        ghoul = await ctx.db_ghoul()

        try:
            await ctx.battle_engine.validate_ghoul(
                ghoul, has_pending_confirmation=lambda g: battles.is_busy(g.telegram_id)
            )
        except FighterIsDeadError:
            await message.reply(ctx.text(Dialogs.ghoul.dead()))
            return
        except FighterNotCombatReadyError as exc:
            await message.reply(
                ctx.text(
                    Dialogs.fight.not_ready(health=exc.health, threshold=exc.threshold)
                )
            )
            return
        except FighterHasPendingBattleError:
            await message.reply(ctx.text(self.busy_text))
            return

        remaining = await ctx.cooldown_remaining(telegram_id, COOLDOWN_NAME)
        if remaining is not None:
            await message.reply(
                ctx.text(
                    Dialogs.mob.cooldown(
                        minutes=remaining.minutes_remaining,
                        seconds=remaining.seconds_remaining,
                    )
                )
            )
            return

        if not await battles.try_claim_mob_fight(telegram_id):
            await message.reply(ctx.text(self.busy_text))
            return

        battle = await ctx.battle_service.fight_mob(
            user, ghoul, is_forced=False, reward_log="mob fight reward"
        )
        await ctx.cooldown_service.set_cooldown(telegram_id, COOLDOWN_NAME)

        await answer_mob_battle(ctx, message, battle, what="mob fight")

        if battle.report.winner == "a":
            outcome = rewards_text(ctx, battle)
        elif battle.report.winner == "b":
            outcome = ctx.text(Dialogs.mob.lost())
        else:
            outcome = ctx.text(Dialogs.mob.draw())

        score = await ctx.battle_service.score(telegram_id, "mob")
        await message.answer(
            ctx.text(
                Dialogs.mob.summary(
                    outcome=outcome,
                    total=score.total,
                    wins=score.wins,
                    losses=score.losses,
                )
            )
        )


class MobFightRouter(BaseRouter[AppContext]):
    handlers = (MobFightHandler,)
