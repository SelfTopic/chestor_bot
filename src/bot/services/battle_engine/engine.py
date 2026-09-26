from __future__ import annotations

import random
from typing import TYPE_CHECKING, Awaitable, Callable, Dict, List, Optional, Protocol, Tuple

from ...exceptions import (
    FighterHasPendingBattleError,
    FighterIsDeadError,
    FighterNotCombatReadyError,
)
from ...game_configs import BATTLE_CONFIG
from ...types import KaguneType
from .core import Battle, BattleResult, EffectiveStats, Fighter, FighterSnapshot
from .mob import MobService

if TYPE_CHECKING:
    from src.database.models import Ghoul

_default_rng = random.Random()


class _KaguneLookup(Protocol):
    def owned_kagune_types(self, ghoul: "Ghoul") -> List[KaguneType]: ...
    def get_kagune_strength(self, ghoul: "Ghoul", kagune_type: KaguneType) -> Optional[int]: ...


class BattleEngine:
    def __init__(self, mob_service: MobService) -> None:
        self._mob_service = mob_service

    async def validate_ghoul(
        self,
        ghoul: "Ghoul",
        has_pending_confirmation: Optional[Callable[["Ghoul"], Awaitable[bool]]] = None,
    ) -> None:
        if ghoul.is_dead:
            raise FighterIsDeadError(ghoul.id)

        if ghoul.health < BATTLE_CONFIG.min_health_to_fight:
            raise FighterNotCombatReadyError(
                ghoul.id, ghoul.health, BATTLE_CONFIG.min_health_to_fight
            )

        if has_pending_confirmation is not None and await has_pending_confirmation(ghoul):
            raise FighterHasPendingBattleError(ghoul.id)

    async def validate_duel(
        self,
        ghoul_a: "Ghoul",
        ghoul_b: "Ghoul",
        has_pending_confirmation: Optional[Callable[["Ghoul"], Awaitable[bool]]] = None,
    ) -> None:
        await self.validate_ghoul(ghoul_a, has_pending_confirmation)
        await self.validate_ghoul(ghoul_b, has_pending_confirmation)

    def ghoul_to_fighter(self, ghoul: "Ghoul", name: str, ghoul_service: _KaguneLookup) -> Fighter:
        kagune_strength: Dict[KaguneType, int] = {}
        for kagune_type in ghoul_service.owned_kagune_types(ghoul):
            strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
            # assert только для pyright: owned_kagune_types уже отбросил None.
            assert strength is not None
            kagune_strength[kagune_type] = strength

        snapshot = FighterSnapshot(
            id=ghoul.id,
            name=name,
            strength=ghoul.strength,
            dexterity=ghoul.dexterity,
            regeneration=ghoul.regeneration,
            speed=ghoul.speed,
            # Текущее health, а не max_health: иначе раненый гуль входил бы в бой с полным
            # пулом.
            health=ghoul.health,
            # max_health в бою не участвует: по нему MobService масштабирует моба.
            max_health=ghoul.max_health,
            hunger=ghoul.hunger,
            is_kakuja=ghoul.is_kakuja,
            kagune_strength=kagune_strength,
        )
        return Fighter(snapshot)

    def run_against_mob(
        self, player: Fighter, rng: random.Random = _default_rng
    ) -> Tuple[BattleResult, Fighter]:
        mob_snapshot = self._mob_service.generate_mob(player.snapshot, rng=rng)
        mob_fighter = Fighter(mob_snapshot)
        result = Battle(player, mob_fighter, compress_hp=True).run(rng=rng)
        return result, mob_fighter

    def run_duel(
        self,
        fighter_a: Fighter,
        fighter_b: Fighter,
        compress_hp: bool = True,
        rng: random.Random = _default_rng,
    ) -> BattleResult:
        return Battle(fighter_a, fighter_b, compress_hp=compress_hp).run(rng=rng)

    @staticmethod
    def power_of(snapshot: FighterSnapshot) -> int:
        return (
            snapshot.strength
            + snapshot.dexterity
            + snapshot.speed
            + snapshot.health
            + snapshot.regeneration
            + snapshot.total_kagune_strength
        )

    @staticmethod
    def effective_power_of(stats: EffectiveStats) -> float:
        return (
            stats.strength
            + stats.dexterity
            + stats.speed
            + stats.health
            + stats.regeneration
            + stats.kagune_strength
        )

    @staticmethod
    def resolve_post_battle_health(
        base_health_before: int, effective_max: float, final_hp: float
    ) -> int:
        if final_hp <= 0:
            return 1

        fraction = final_hp / effective_max if effective_max > 0 else 0.0
        return max(1, round(base_health_before * fraction))


__all__ = ["BattleEngine"]
