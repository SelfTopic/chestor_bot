"""
Бой с мобом: общий для "бить моба" (mob_fight.py, добровольный) и засады в
"сожрать человека" (eat_human.py, принудительный). У прода это две копии одного
кода, различаются только is_forced в истории боёв и строкой лога начисления.

ActiveBattle-лок (try_claim_mob_fight) берёт вызывающий: у засады "лок занят"
значит "засады не было", а у "бить моба" это отказ. Отпускает лок run_mob_battle.
"""

import random
from dataclasses import dataclass
from typing import Any

from selfrot.types import Message

from src.bot.game_configs import MOB_CONFIG
from src.bot.services import BattleService
from src.bot.services.battle_engine.core import BattleResult, Fighter
from src.bot.utils import utcnow_naive
from src.database.models import Ghoul, User

from ...context import AppContext
from .battle_text import answer_battle


@dataclass(frozen=True)
class MobBattle:
    result: BattleResult
    player: Fighter
    mob: Fighter
    reward_level_progress: float | None
    reward_rc: int | None
    reward_cheston: int | None

    @property
    def winner(self) -> str | None:
        """ "a" — игрок, "b" — моб, None — ничья."""
        return self.result.winner

    def rewards_text(self) -> str:
        """Строки наград за победу, одинаковые у обоих видов боя."""
        text = f"📈 Получено опыта: {self.reward_level_progress:.2f}%"
        text += f"\n💰 Получено CheSton: {self.reward_cheston}"
        if self.reward_rc:
            text += f"\n♦️ Дополнительно найдено: {self.reward_rc} RC-клеток!"
        return text


async def run_mob_battle(
    ctx: AppContext[Any],
    user: User,
    ghoul: Ghoul,
    *,
    is_forced: bool,
    reward_log: str,
) -> MobBattle:
    """Бой, здоровье после боя, награды за победу, запись в историю, снятие лока."""
    telegram_id = ghoul.telegram_id
    ghoul_service = ctx.ghoul_service
    battle_service = ctx.battle_service

    player = battle_service.ghoul_to_fighter(ghoul, user.full_name, ghoul_service)
    result, mob = battle_service.run_against_mob(player)

    new_health = BattleService.resolve_post_battle_health(
        ghoul.health, result.stats_a.health, result.final_hp_a
    )
    await ghoul_service.set_fields(
        telegram_id, health=new_health, health_updated_at=utcnow_naive()
    )

    reward_level_progress = None
    reward_rc = None
    reward_cheston = None

    if result.winner == "a":
        mob_power = battle_service.power_of(mob.snapshot)
        player_power = ghoul_service.calculate_power(ghoul)
        # BATTLE_DESIGN.md "Формула левел-апа": 1%*(сила соперника/своя сила), как
        # у дуэли, но ÷5: фарм мобов медленнее PvP.
        reward_level_progress = (
            (mob_power / player_power) / MOB_CONFIG.level_progress_divisor
            if player_power > 0
            else 0.0
        )
        await ctx.level_up_service.add_progress(telegram_id, reward_level_progress)

        if random.random() < MOB_CONFIG.rc_drop_chance:
            reward_rc = random.randint(MOB_CONFIG.rc_drop_min, MOB_CONFIG.rc_drop_max)
            await ghoul_service.increment_fields(telegram_id, rc_money=reward_rc)

        # ECONOMY.md часть 4: CheSton за победу привязан к цене прокачки
        # эталонного стата на текущем уровне.
        reward_cheston = MOB_CONFIG.cheston_reward_for_mob_win(ghoul.level)
        await ctx.user_service.plus_balance(
            telegram_id, change_balance=reward_cheston, log=reward_log
        )

    battles = ctx.battle_record_service
    await battles.record_mob_fight(
        telegram_id=telegram_id,
        mob_name=mob.name,
        winner=result.winner,
        ended_naturally=result.ended_naturally,
        is_forced=is_forced,
        reward_level_progress=reward_level_progress,
        reward_rc=reward_rc,
        reward_balance=reward_cheston,
    )
    await battles.release(telegram_id)

    return MobBattle(
        result, player, mob, reward_level_progress, reward_rc, reward_cheston
    )


async def answer_mob_battle(
    ctx: AppContext[Any], message: Message, battle: MobBattle, *, what: str
) -> None:
    ghoul_service = ctx.ghoul_service
    battle_service = ctx.battle_service
    rank_a = ghoul_service.get_danger_rank(
        battle_service.power_of(battle.player.snapshot)
    )
    rank_b = ghoul_service.get_danger_rank(battle_service.power_of(battle.mob.snapshot))

    await answer_battle(
        message,
        ctx.battle_text_generator,
        battle.result,
        battle.player,
        battle.mob,
        rank_a,
        rank_b,
        what=what,
    )
