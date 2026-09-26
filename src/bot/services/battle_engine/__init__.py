"""Боевой движок. `core/` - чистый домен без БД (статы, формулы, раунды,
Battle/Fighter). `BattleService`/`MobService` -
мосты между игровым миром (Ghoul из БД) и движком. Показ боя игроку -
`routers/ghoul_routers/battle_text_generator.py`."""

from .battle_service import BattleService
from .core import (
    AttackAction,
    AttackType,
    Battle,
    BattleResult,
    DefenseAction,
    EffectiveStats,
    FastAttackAction,
    Fighter,
    FighterSnapshot,
    HitResult,
    IdleAction,
    InvalidBattleStatsError,
    RegenAction,
    RoundAction,
    RoundActionType,
    RoundResult,
)
from .mob import MobService

__all__ = [
    "BattleService",
    "MobService",
    "AttackAction",
    "AttackType",
    "Battle",
    "BattleResult",
    "DefenseAction",
    "EffectiveStats",
    "FastAttackAction",
    "Fighter",
    "FighterSnapshot",
    "HitResult",
    "IdleAction",
    "InvalidBattleStatsError",
    "RegenAction",
    "RoundAction",
    "RoundActionType",
    "RoundResult",
]
