"""
Вся честная математика боя - чистые функции без состояния и без
"владельца"-объекта (BATTLE_ENGINE.md, части 1-2). Сознательно НЕ классы -
дискуссия в чате: жалоба автора была про файловую организацию и
отсутствие состояния как объекта (см. Fighter/Battle), а не про то, что
чистые функции сами по себе плохая архитектура.

Модуль чистый - никакого доступа к БД/сервисам (та же дисциплина, что и в
regen_calculate.py).
"""

from __future__ import annotations

import random
from enum import Enum
from typing import TYPE_CHECKING

from ....game_configs import BATTLE_CONFIG

if TYPE_CHECKING:
    from .fighter import EffectiveStats

# Собственный экземпляр, чтобы был реальный тип random.Random (не модуль
# random) без лишних Optional-проверок у вызывающего кода. Тесты передают
# свой сид явно.
_default_rng = random.Random()


class AttackType(Enum):
    """Чем нанесён один конкретный удар - физически или кагуне. НЕ путать
    с RoundActionType (actions.py) - это про раунд целиком (атаковал
    /регенерировал), а это - про то, чем именно бил."""

    PHYSICAL = "physical"
    KAGUNE = "kagune"


# --- Уклонение (2.3) --------------------------------------------------------

_DODGE_FLOOR = 5.0
_DODGE_CEILING = 95.0
_DODGE_BASE_SCALE = 90.0
_DODGE_BASE_DIVISOR = 10000.0


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _dodge_base(dexterity: float) -> float:
    return _clamp(
        _DODGE_FLOOR + (dexterity / _DODGE_BASE_DIVISOR) * _DODGE_BASE_SCALE,
        _DODGE_FLOOR,
        _DODGE_CEILING,
    )


def dodge_chance(defender_dexterity: float, attacker_dexterity: float) -> float:
    """Шанс защищающегося полностью избежать удара, см. BATTLE_ENGINE.md 2.3.
    Симметрично устроено - неважно, кто из двух передан "защищающимся"."""

    weaker = min(defender_dexterity, attacker_dexterity)
    stronger = max(defender_dexterity, attacker_dexterity)
    base = _dodge_base(weaker)

    if defender_dexterity <= attacker_dexterity:
        return base
    return _clamp(base * (stronger / weaker), _DODGE_FLOOR, _DODGE_CEILING)


# --- Лишний удар от speed (1.4 / 2.4a) --------------------------------------


def extra_hit_percent(speed_defender: float, speed_attacker: float) -> float:
    """Шанс (в процентах, может быть > 100) для АТАКУЮЩЕГО нанести лишний
    удар в этом раунде - чисто из отношения скоростей, без базового пола,
    см. BATTLE_ENGINE.md 1.4. Аргумент "speed_defender" - скорость ВТОРОГО
    бойца (не защита в смысле 2.4c, а просто "тот, с кем сравниваем")."""

    hi = max(speed_attacker, speed_defender)
    lo = min(speed_attacker, speed_defender)
    if hi <= 0:
        return 0.0

    diff_ratio = (hi - lo) / hi
    if speed_attacker >= speed_defender:
        return diff_ratio * 200.0
    return diff_ratio * 100.0


def resolve_hit_chain(percent: float, rng: random.Random) -> int:
    """Проценты свыше 100 не клэмпятся, а превращаются в цепочку
    гарантированных ударов + один вероятностный остаток, см.
    BATTLE_ENGINE.md 2.4a. Возвращает количество ДОПОЛНИТЕЛЬНЫХ ударов
    (не считая базового первого)."""

    guaranteed = 0
    remaining = percent
    while remaining > 100.0:
        remaining -= 100.0
        guaranteed += 1

    if rng.random() * 100.0 < remaining:
        guaranteed += 1

    return guaranteed


def resolve_extra_hit_counts(
    speed_a: float, speed_b: float, rng: random.Random
) -> tuple[int, int]:
    """Только БОНУСНЫЕ удары от скорости (0, 1 или 2 по текущей формуле) -
    БЕЗ гарантированного "+1" за само действие. Раньше "+1" был зашит сюда
    же (см. историю - было resolve_hit_count), но после того как
    регенерация стала полноценным альтернативным действием на раунд,
    "+1" больше не всегда применим - это решает Battle/Fighter.decide_action
    (RoundActionType.ATTACK даёт "+1" сам, RoundActionType.REGEN - нет,
    но бонусные удары отсюда получает в любом случае - см.
    REGENERATION.md)."""

    pct_a = extra_hit_percent(speed_defender=speed_b, speed_attacker=speed_a)
    pct_b = extra_hit_percent(speed_defender=speed_a, speed_attacker=speed_b)
    return resolve_hit_chain(pct_a, rng), resolve_hit_chain(pct_b, rng)


# --- Тип атаки: первый удар физический, дальше -10% за физический удар -----


def attack_type_chance(physical_hits_landed: int) -> float:
    """Шанс, что СЛЕДУЮЩИЙ удар этого бойца будет физическим, а не кагуне -
    не честная монетка. Первый удар за весь бой гарантированно физический
    (physical_hits_landed=0 -> 100%), дальше -10 п.п. за КАЖДЫЙ реально
    нанесённый физический удар - удар кагуне счётчик не двигает вообще.
    См. BATTLE_ENGINE.md ("Тип атаки")."""

    return max(
        0.0,
        100.0 - BATTLE_CONFIG.physical_attack_decay_percent * physical_hits_landed,
    )


# --- Гейт кагуне-защиты (2.4c шаг 2) ----------------------------------------


def kagune_gate_chance(defender_dex_speed: float, attacker_dex_speed: float) -> float:
    """Шанс защищающегося успеть поднять кагуне для защиты этого удара -
    см. BATTLE_ENGINE.md 2.4c шаг 2. При равных статах - ровно половина."""

    if attacker_dex_speed <= 0:
        return 100.0
    return min(
        100.0,
        BATTLE_CONFIG.kagune_gate_base_percent * defender_dex_speed / attacker_dex_speed,
    )


def resolve_block_percent(
    kagune_up: bool,
    attack_type: AttackType,
    attacker: "EffectiveStats",
    defender: "EffectiveStats",
    rng: random.Random,
) -> float:
    """4 ветки блока, см. BATTLE_ENGINE.md 2.4c. margin>=0 - это ПОРОГ
    (своя сила >= чужой), не сама вероятность в процентах - величина
    margin на размер блока не влияет."""

    if kagune_up:
        if attack_type is AttackType.PHYSICAL:
            return rng.uniform(
                BATTLE_CONFIG.physical_block_min, BATTLE_CONFIG.physical_block_max
            )
        margin = defender.kagune_strength - attacker.kagune_strength
        if margin >= 0:
            return rng.uniform(
                BATTLE_CONFIG.modest_block_min, BATTLE_CONFIG.modest_block_max
            )
        return 0.0

    if attack_type is AttackType.PHYSICAL:
        margin = defender.health - attacker.health
        if margin >= 0:
            return rng.uniform(
                BATTLE_CONFIG.modest_block_min, BATTLE_CONFIG.modest_block_max
            )
        return 0.0

    # Кагуне не поднят, бьют кагуне - голое тело кагуне-оружие не держит.
    return 0.0


def raw_damage(
    attack_type: AttackType, attacker: "EffectiveStats", rng: random.Random
) -> float:
    variance = rng.uniform(
        BATTLE_CONFIG.damage_variance_min, BATTLE_CONFIG.damage_variance_max
    )
    if attack_type is AttackType.PHYSICAL:
        return variance * attacker.strength
    return variance * (attacker.strength + attacker.kagune_strength)


def raw_fast_attack_damage(
    attack_type: AttackType, attacker: "EffectiveStats", rng: random.Random
) -> float:
    """То же самое, что raw_damage, но для БОНУСНОГО удара от speed
    (FastAttack) - см. BATTLE_CONFIG.fast_attack_damage_variance_min/max:
    некогда вкладываться в силу удара, если бьёшь походя за счёт скорости,
    поэтому диапазон ниже и смещён вниз, а не просто у'же вокруг 1.0."""

    variance = rng.uniform(
        BATTLE_CONFIG.fast_attack_damage_variance_min,
        BATTLE_CONFIG.fast_attack_damage_variance_max,
    )
    if attack_type is AttackType.PHYSICAL:
        return variance * attacker.strength
    return variance * (attacker.strength + attacker.kagune_strength)


# --- Регенерация в бою (REGENERATION.md) ------------------------------------


def regen_proc_chance(own_regeneration: float, opponent_regeneration: float) -> float:
    """Шанс ВТОРОГО (после гарантированного) прока регенерации - та же
    форма, что у extra_hit_percent (сравнение своей регенерации с чужой),
    но клэмп на 100% - здесь не строится цепочка, всего один бросок."""

    hi = max(own_regeneration, opponent_regeneration)
    lo = min(own_regeneration, opponent_regeneration)
    if hi <= 0:
        return 0.0

    diff_ratio = (hi - lo) / hi
    if own_regeneration >= opponent_regeneration:
        return min(100.0, diff_ratio * 200.0)
    return diff_ratio * 100.0


__all__ = [
    "AttackType",
    "dodge_chance",
    "extra_hit_percent",
    "resolve_hit_chain",
    "resolve_extra_hit_counts",
    "attack_type_chance",
    "kagune_gate_chance",
    "resolve_block_percent",
    "raw_damage",
    "raw_fast_attack_damage",
    "regen_proc_chance",
]
