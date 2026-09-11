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
from .mob import MobService
from .text_generator import MAX_WIDTH_TEXT_RICH_MESSAGE, BattleTextGenerator

__all__ = [
    "BattleTextGenerator",
    "MAX_WIDTH_TEXT_RICH_MESSAGE",
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
