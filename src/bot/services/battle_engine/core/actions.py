"""
Классификация того, ЧТО именно боец сделал за раунд - обсуждение в чате
(REGENERATION.md, "движок был просто примеркой цифр"): раньше RoundResult
был плоским набором полей (hits_by_a/regen_to_a/...), и по нему нельзя
было честно понять, что произошло. Теперь у каждого участника раунда -
СПИСОК действий (Round.actions_a/actions_b), потому что за один раунд
может случиться больше одного: например регенерация (основное действие)
+ бонусный удар от speed (FastAttack) в одном и том же раунде.

Отдельный dataclass на каждый ВИД действия (а не Enum + if/elif, как у
NotificationTicker) - осознанное отступление от остального стиля проекта,
специально ради будущего рендерера: `match action: case AttackAction():
... case RegenAction(): ...` вместо чтения кучи optional-полей."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .hit import HitResult


class RoundActionType(Enum):
    """ОСНОВНОЕ действие бойца за раунд - решает Fighter.decide_action().
    DEFENSE и IDLE существуют уже сейчас, чтобы не перекраивать типы
    заново, когда для них появится механика - decide_action их пока
    никогда не возвращает."""

    ATTACK = "attack"
    REGEN = "regen"
    DEFENSE = "defense"  # зарезервировано, механики ещё нет
    IDLE = "idle"  # зарезервировано, механики ещё нет


@dataclass(frozen=True)
class AttackAction:
    """Гарантированный "базовый" удар - результат ОСНОВНОГО действия
    ATTACK. Резолвится через resolve_hit, как и FastAttackAction ниже -
    разница чисто в классификации для рендера, не в механике удара."""

    hit: "HitResult"


@dataclass(frozen=True)
class FastAttackAction:
    """Бонусный удар от speed (formulas.resolve_extra_hit_counts) -
    случается НЕЗАВИСИМО от основного действия, в том числе если основное
    действие в этом раунде - RegenAction (см. REGENERATION.md: "быстрый
    гуль после регенерации ещё и может успеть ударить")."""

    hit: "HitResult"


@dataclass(frozen=True)
class RegenAction:
    """Основное действие - регенерация ВМЕСТО атаки (REGENERATION.md).
    was_guaranteed=True - первый (гарантированный) прок за бой,
    False - второй (вероятностный, максимум один раз за бой)."""

    healed: float
    was_guaranteed: bool


@dataclass(frozen=True)
class DefenseAction:
    """Зарезервировано - осознанная концентрация на защите вместо атаки.
    Механика не спроектирована, класс существует, чтобы тип действия был
    известен заранее (см. BATTLE_ENGINE.md часть 7, точка расширения)."""


@dataclass(frozen=True)
class IdleAction:
    """Зарезервировано - раунд без действия (например будущий стан/пропуск
    хода). Механика не спроектирована."""


RoundAction = Union[AttackAction, FastAttackAction, RegenAction, DefenseAction, IdleAction]


__all__ = [
    "RoundActionType",
    "AttackAction",
    "FastAttackAction",
    "RegenAction",
    "DefenseAction",
    "IdleAction",
    "RoundAction",
]
