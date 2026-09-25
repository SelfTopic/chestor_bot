"""
"реген" и "голод": пассивные показатели гуля, только чтение. Формулы (регенерация,
тиры голода, эффективные статы через Fighter) берутся из прод-кода как есть.
"""

from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.utils import (
    format_duration,
    get_hunger_tier,
    health_regen_per_hour,
    hours_until_full_health,
    hours_until_starved,
)

from ...context import AppContext
from ...types import TextUserMessage
from ...utils import full_name


class RegenStatusHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("реген", ignore_case=True) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        ghoul = await ctx.db_ghoul()

        hp_per_hour = health_regen_per_hour(
            regeneration=ghoul.regeneration,
            hunger=ghoul.hunger,
            kagune_type_bit=ghoul.kagune_type_bit or 0,
            is_kakuja=ghoul.is_kakuja,
        )
        hours_left = hours_until_full_health(
            ghoul.health, ghoul.max_health, hp_per_hour
        )

        if hours_left == 0.0:
            time_left = "Уже полностью здоров(а)."
        elif hours_left is None:
            time_left = (
                "При текущей скорости регенерации здоровье само не восстановится."
            )
        else:
            time_left = (
                f"До полного здоровья: {format_duration(int(hours_left * 3600))}"
            )

        await ctx.message.answer(
            ctx.dialog_service.text(
                key="regen_status",
                health=ghoul.health,
                max_health=ghoul.max_health,
                hp_per_hour=round(hp_per_hour, 2),
                time_left=time_left,
            )
        )


class HungerStatusHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("голод", ignore_case=True) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        ghoul = await ctx.db_ghoul()

        hours_left = hours_until_starved(ghoul.hunger, ghoul.is_kakuja)
        tier = get_hunger_tier(ghoul.hunger)

        if hours_left <= 0:
            time_left = "Голод уже на нуле."
        else:
            time_left = f"До истощения: {format_duration(int(hours_left * 3600))}"

        # Не только тир, но и его активные множители и итоговые эффективные статы
        # (BATTLE_ENGINE.md 8.3). Fighter собирается только ради compute_effective_stats,
        # боя тут нет.
        fighter = ctx.battle_engine.ghoul_to_fighter(
            ghoul, full_name(ctx.message.user), ctx.ghoul_service
        )
        stats = fighter.stats

        await ctx.message.answer(
            ctx.dialog_service.text(
                key="hunger_status",
                hunger=ghoul.hunger,
                tier=tier.name,
                time_left=time_left,
                falling_multiplier=tier.falling_multiplier,
                rising_multiplier=tier.rising_multiplier,
                effective_strength=round(stats.strength, 1),
                effective_dexterity=round(stats.dexterity, 1),
                effective_speed=round(stats.speed, 1),
                effective_health=round(stats.health, 1),
                effective_regeneration=round(stats.regeneration, 1),
                effective_kagune_strength=round(stats.kagune_strength, 1),
            )
        )


class PassiveStatusRouter(BaseRouter[AppContext]):
    handlers = (RegenStatusHandler, HungerStatusHandler)
