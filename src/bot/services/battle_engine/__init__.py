"""Боевой движок. `core/` - чистый домен без БД (статы, формулы, раунды,
Battle/Fighter). Слой оркестрации (роутеры, сохранение BattleLog в БД) -
будущая задача, сюда пока ничего не добавлено."""

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
from .text_generator import BattleTextGenerator

__all__ = [
    "BattleTextGenerator",
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
