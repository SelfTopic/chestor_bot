from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.dialogs import Dialogs
from src.bot.utils import (
    format_duration,
    get_hunger_tier,
    health_regen_per_hour,
    hours_until_full_health,
    hours_until_starved,
)

from ...context import AppContext
from ..types import TextUserMessage
from ..utils import full_name


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
            time_left = Dialogs.status.healthy()
        elif hours_left is None:
            time_left = Dialogs.status.no_regen()
        else:
            time_left = Dialogs.status.until_healthy(
                duration=format_duration(int(hours_left * 3600))
            )

        await ctx.say(
            Dialogs.status.regen(
                health=ghoul.health,
                max_health=ghoul.max_health,
                hp_per_hour=round(hp_per_hour, 2),
                time_left=ctx.text(time_left),
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
            time_left = Dialogs.status.starved()
        else:
            time_left = Dialogs.status.until_starved(
                duration=format_duration(int(hours_left * 3600))
            )

        fighter = ctx.battle_engine.ghoul_to_fighter(
            ghoul, full_name(ctx.message.user), ctx.ghoul_service
        )
        stats = fighter.stats

        await ctx.say(
            Dialogs.status.hunger(
                hunger=ghoul.hunger,
                tier=tier.name,
                time_left=ctx.text(time_left),
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
