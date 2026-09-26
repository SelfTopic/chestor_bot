from __future__ import annotations

import random

from ...game_configs import MOB_CONFIG
from .core import FighterSnapshot

_default_rng = random.Random()

# Пол в 1: validate_snapshot требует dexterity и speed больше нуля, а round() при множителе
# 0.5 может дать 0.
_MIN_POSITIVE_STAT = 1


class MobService:
    def generate_mob(
        self, player_snapshot: FighterSnapshot, rng: random.Random = _default_rng
    ) -> FighterSnapshot:
        multiplier = rng.uniform(MOB_CONFIG.stat_multiplier_min, MOB_CONFIG.stat_multiplier_max)
        vacuum_health = (
            player_snapshot.max_health
            if player_snapshot.max_health is not None
            else player_snapshot.health
        )

        return FighterSnapshot(
            id=-1,
            name=rng.choice(MOB_CONFIG.names),
            strength=max(0, round(player_snapshot.strength * multiplier)),
            dexterity=max(_MIN_POSITIVE_STAT, round(player_snapshot.dexterity * multiplier)),
            regeneration=max(0, round(player_snapshot.regeneration * multiplier)),
            speed=max(_MIN_POSITIVE_STAT, round(player_snapshot.speed * multiplier)),
            health=max(_MIN_POSITIVE_STAT, round(vacuum_health * multiplier)),
            hunger=100,
            is_kakuja=False,
            kagune_strength={},
        )


__all__ = ["MobService"]
