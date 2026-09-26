"""
"боевая мощь" (rich-таблицы, текстом при ошибке rich) и короткий алиас "бм"
(два числа: мощь вне боя и в бою прямо сейчас).

Ветка "мёртвый гуль" недостижима (GhoulMiddleware не пускает мёртвых), но
оставлена как у прода.
"""

from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasUser, Text

from src.database.models import Ghoul, User

from ....context import AppContext
from ...types import TextUserMessage
from ...rich import answer_rich_or_text
from .tables import combat_power_rich


class CombatPowerHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("боевая мощь", ignore_case=True) & HasUser()

    def plain_text(self, user: User, ghoul: Ghoul, danger_rank: str) -> str:
        ctx = self.ctx
        ghoul_service = ctx.ghoul_service
        engine = ctx.battle_engine

        fighter = engine.ghoul_to_fighter(ghoul, user.full_name, ghoul_service)
        stats = fighter.stats
        return ctx.dialog_service.text(
            key="combat_power",
            name=user.full_name,
            danger_rank=danger_rank,
            vacuum_strength=ghoul.strength,
            effective_strength=round(stats.strength, 1),
            vacuum_dexterity=ghoul.dexterity,
            effective_dexterity=round(stats.dexterity, 1),
            vacuum_speed=ghoul.speed,
            effective_speed=round(stats.speed, 1),
            vacuum_health=ghoul.max_health,
            effective_health=round(stats.health, 1),
            vacuum_regeneration=ghoul.regeneration,
            effective_regeneration=round(stats.regeneration, 1),
            vacuum_kagune=ghoul_service.total_kagune_strength(ghoul),
            effective_kagune=round(stats.kagune_strength, 1),
            vacuum_power=ghoul_service.calculate_power(ghoul),
            effective_power=round(engine.effective_power_of(stats), 1),
        )

    async def handle(self) -> None:
        ctx = self.ctx
        user = await ctx.db_user()
        ghoul = await ctx.db_ghoul()

        if ghoul.is_dead:
            await ctx.message.answer(
                ctx.dialog_service.text(key="dead_ghoul_profile", name=user.full_name)
            )
            return

        ghoul_service = ctx.ghoul_service
        danger_rank = ghoul_service.get_danger_rank(
            ghoul_service.calculate_power(ghoul)
        )

        await answer_rich_or_text(
            ctx.message,
            combat_power_rich(
                user, ghoul, danger_rank, ghoul_service, ctx.battle_engine
            ),
            lambda: self.plain_text(user, ghoul, danger_rank),
            what="combat power",
        )


class CombatPowerShortHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("бм", ignore_case=True) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        user = await ctx.db_user()
        ghoul = await ctx.db_ghoul()

        if ghoul.is_dead:
            await ctx.message.answer(
                ctx.dialog_service.text(key="dead_ghoul_profile", name=user.full_name)
            )
            return

        fighter = ctx.battle_engine.ghoul_to_fighter(
            ghoul, user.full_name, ctx.ghoul_service
        )
        await ctx.message.answer(
            ctx.dialog_service.text(
                key="combat_power_short",
                vacuum_power=ctx.ghoul_service.calculate_power(ghoul),
                effective_power=round(
                    ctx.battle_engine.effective_power_of(fighter.stats), 1
                ),
            )
        )


class CombatPowerRouter(BaseRouter[AppContext]):
    handlers = (CombatPowerHandler, CombatPowerShortHandler)
