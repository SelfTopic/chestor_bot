"""
Сервисы, нужные дуэли целиком, одним набором: в хендлере они берутся из ctx, а в
DuelTicker (таймауты) собираются из контейнера на собственной сессии тикера. fight.py
не знает, откуда его вызвали. Замена прод-services.py (там build_services собирал
всё вручную, в том числе LevelUpService с aiogram Bot).
"""

from dataclasses import dataclass
from typing import Any

from src.bot.containers import Container
from src.bot.services import BattleRecordService, BattleTextGenerator, DuelService
from src.bot.services.dialog import DialogService

from ....context import AppContext
from ....repositories.battle import FightRepository
from ....services.battle import BattleService
from ....services.level_up import LevelUpService
from ....services.notify import Notifier


@dataclass(frozen=True)
class DuelServices:
    battle: BattleService
    battle_text_generator: BattleTextGenerator
    battle_record_service: BattleRecordService
    duel_service: DuelService

    @classmethod
    def from_ctx(cls, ctx: AppContext[Any]) -> "DuelServices":
        return cls(
            battle=ctx.battle_service,
            battle_text_generator=ctx.battle_text_generator,
            battle_record_service=ctx.battle_record_service,
            duel_service=ctx.duel_service,
        )

    @classmethod
    def from_container(
        cls, container: Container, dialog_service: DialogService, notifier: Notifier
    ) -> "DuelServices":
        """Сессию БД контейнер берёт из session_context: вызывающий ставит её сам,
        как DatabaseMiddleware."""
        user_service = container.user_service()
        ghoul_service = container.ghoul_service()
        battle_record_service = container.battle_record_service()
        duel_service = container.duel_service()
        battle = BattleService(
            engine=container.battle_service(),
            fights=FightRepository(container.db_session(), container.ghoul_repository()),
            ghoul_service=ghoul_service,
            user_service=user_service,
            level_up_service=LevelUpService(
                user_service, ghoul_service, dialog_service, notifier
            ),
            battle_record_service=battle_record_service,
            duel_service=duel_service,
        )
        return cls(
            battle=battle,
            battle_text_generator=container.battle_text_generator(),
            battle_record_service=battle_record_service,
            duel_service=duel_service,
        )
