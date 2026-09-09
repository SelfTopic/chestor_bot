"""
Раундовый боевой движок - честная посимвольная симуляция, см.
BATTLE_ENGINE.md (части 0-2) и BATTLE_DESIGN.md ("Множители типов кагуне").

Модуль чистый - никакого доступа к БД/сервисам, только dataclass'ы и
функции над скалярами (та же дисциплина, что и в regen_calculate.py).
Собрать FighterSnapshot из реального Ghoul - забота вызывающего кода
(будущий BattleService), здесь только сами формулы и цикл раундов.

Порядок цепочки модификаторов везде один и тот же (BATTLE_DESIGN.md):
база -> голод-тир -> тип кагуне -> какудж (сверху поверх всего).
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from ..game_configs import BATTLE_CONFIG, PASSIVE_STATS_CONFIG
from ..types import KaguneType
from .regen_calculate import get_hunger_tier

# Как и в regen_calculate.py - собственный экземпляр, чтобы был реальный
# тип random.Random (не модуль random) без лишних Optional-проверок у
# вызывающего кода. Тесты передают свой сид явно.
_default_rng = random.Random()


class InvalidBattleStatsError(ValueError):
    """2.4d - если у бойца обнаружены невозможные статы (например
    dexterity<=0), бой не считается вообще, а не падает делением на 0."""


class AttackType(Enum):
    PHYSICAL = "physical"
    KAGUNE = "kagune"


# --- Таблица типов кагуне (BATTLE_DESIGN.md "Множители типов кагуне") -----

# Множитель на каждый стат, который данный тип трогает. kagune_strength
# сюда осознанно не входит - исключён в доке ("НЕ сила кагуне"), получает
# только голод+какудж (см. compute_effective_stats).
KAGUNE_TYPE_MULTIPLIERS: Dict[KaguneType, Dict[str, float]] = {
    KaguneType.UKAKU: {"speed": 1.8},
    KaguneType.KOUKAKU: {"strength": 1.6, "speed": 1.3},
    KaguneType.RINKAKU: {
        "dexterity": 1.3,
        "regeneration": 1.8,
        "speed": 1.5,
        "health": 1.5,
    },
    KaguneType.BIKAKU: {
        "strength": 1.5,
        "dexterity": 1.4,
        "regeneration": 1.4,
        "speed": 1.4,
        "health": 1.4,
    },
}

# У каждого типа один "приоритетный" стат - при нескольких открытых типах,
# трогающих один стат, побеждает хозяин (если он среди открытых), иначе
# min() (см. BATTLE_DESIGN.md, правило стаков).
KAGUNE_TYPE_PRIORITY_STAT: Dict[KaguneType, str] = {
    KaguneType.UKAKU: "speed",
    KaguneType.KOUKAKU: "strength",
    KaguneType.RINKAKU: "regeneration",
    KaguneType.BIKAKU: "health",
}

# "Растущие" статы под голодом (получают rising_multiplier тира) - см.
# BATTLE_DESIGN.md "Множители голода". Всё остальное боевое - "падающее".
# health сюда отнесён по аналогии с dexterity/regeneration/speed
# ("выносливость слабеет при голоде") - явно нигде не решалось, это
# рабочее предположение, не зафиксированный факт.
_RISING_HUNGER_STATS = {"strength", "kagune_strength"}


def resolve_kagune_multiplier(stat: str, owned_types: List[KaguneType]) -> float:
    """Множитель типа кагуне для одного стата - приоритет + min()-fallback,
    см. BATTLE_DESIGN.md, правило стаков."""

    touching = [t for t in owned_types if stat in KAGUNE_TYPE_MULTIPLIERS.get(t, {})]
    if not touching:
        return 1.0

    owner = next((t for t in touching if KAGUNE_TYPE_PRIORITY_STAT[t] == stat), None)
    if owner is not None:
        return KAGUNE_TYPE_MULTIPLIERS[owner][stat]

    return min(KAGUNE_TYPE_MULTIPLIERS[t][stat] for t in touching)


# --- Снапшот бойца и эффективные (боевые) статы ---------------------------


@dataclass(frozen=True)
class FighterSnapshot:
    """Всё, что нужно движку про одного бойца - вакуумные (профильные)
    значения ДО цепочки модификаторов. `kagune_strength` - только открытые
    типы (как nullable-колонки в Ghoul), не все 4 подряд."""

    id: int
    name: str
    strength: int
    dexterity: int
    regeneration: int
    speed: int
    health: int
    hunger: int
    is_kakuja: bool
    kagune_strength: Dict[KaguneType, int] = field(default_factory=dict)

    @property
    def owned_kagune_types(self) -> List[KaguneType]:
        return list(self.kagune_strength.keys())

    @property
    def total_kagune_strength(self) -> int:
        return sum(self.kagune_strength.values())


@dataclass(frozen=True)
class EffectiveStats:
    """Боевые (эффективные) статы ПОСЛЕ полной цепочки модификаторов - то,
    чем боец реально дерётся прямо сейчас, см. BATTLE_ENGINE.md 4.2."""

    strength: float
    dexterity: float
    regeneration: float
    speed: float
    health: float
    kagune_strength: float


def validate_snapshot(fighter: FighterSnapshot) -> None:
    """2.4d - невозможные статы отменяют бой, а не роняют деление на 0."""

    if fighter.dexterity <= 0 or fighter.speed <= 0:
        raise InvalidBattleStatsError(
            f"Fighter {fighter.id} ({fighter.name}): dexterity/speed must be > 0, "
            f"got dexterity={fighter.dexterity}, speed={fighter.speed}"
        )
    if fighter.strength < 0 or fighter.regeneration < 0 or fighter.health <= 0:
        raise InvalidBattleStatsError(
            f"Fighter {fighter.id} ({fighter.name}): strength/regeneration must be "
            f">= 0 and health > 0, got strength={fighter.strength}, "
            f"regeneration={fighter.regeneration}, health={fighter.health}"
        )
    if not 0 <= fighter.hunger <= 100:
        raise InvalidBattleStatsError(
            f"Fighter {fighter.id} ({fighter.name}): hunger must be in [0, 100], "
            f"got hunger={fighter.hunger}"
        )
    if any(value < 0 for value in fighter.kagune_strength.values()):
        raise InvalidBattleStatsError(
            f"Fighter {fighter.id} ({fighter.name}): kagune_strength values must "
            f"be >= 0, got {fighter.kagune_strength}"
        )


def compute_effective_stats(fighter: FighterSnapshot) -> EffectiveStats:
    """База -> голод-тир -> тип кагуне -> какудж, см. BATTLE_ENGINE.md 1.3.
    `health` эффективный может честно превысить вакуумный `max_health`
    профиля (не участвует здесь вообще - он не боевой стат, см. 4.2)."""

    tier = get_hunger_tier(fighter.hunger)
    owned = fighter.owned_kagune_types
    kakuja_mult = PASSIVE_STATS_CONFIG.kakuja_multiplier if fighter.is_kakuja else 1.0

    def chain(base: float, stat_name: str, is_rising: bool) -> float:
        hunger_mult = tier.rising_multiplier if is_rising else tier.falling_multiplier
        kagune_mult = resolve_kagune_multiplier(stat_name, owned)
        return base * hunger_mult * kagune_mult * kakuja_mult

    strength = chain(fighter.strength, "strength", is_rising=True)
    dexterity = chain(fighter.dexterity, "dexterity", is_rising=False)
    regeneration = chain(fighter.regeneration, "regeneration", is_rising=False)
    speed = chain(fighter.speed, "speed", is_rising=False)
    health = chain(fighter.health, "health", is_rising=False)

    # kagune_strength сознательно НЕ идёт через resolve_kagune_multiplier -
    # исключён из таблицы типов кагуне, только голод (растущий) + какудж.
    kagune_strength = (
        fighter.total_kagune_strength * tier.rising_multiplier * kakuja_mult
    )

    return EffectiveStats(
        strength=strength,
        dexterity=dexterity,
        regeneration=regeneration,
        speed=speed,
        health=health,
        kagune_strength=kagune_strength,
    )


# --- Уклонение (2.3) -------------------------------------------------------

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


# --- Лишний удар от speed (1.4 / 2.4a) -------------------------------------


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


def resolve_hit_count(
    speed_a: float, speed_b: float, rng: random.Random
) -> tuple:
    """Итоговое число ударов за раунд для (a, b) - 1 базовый + цепочка
    лишних из extra_hit_percent/resolve_hit_chain."""

    pct_a = extra_hit_percent(speed_defender=speed_b, speed_attacker=speed_a)
    pct_b = extra_hit_percent(speed_defender=speed_a, speed_attacker=speed_b)
    return (
        1 + resolve_hit_chain(pct_a, rng),
        1 + resolve_hit_chain(pct_b, rng),
    )


# --- Один удар: гейт кагуне-защиты, тип атаки, блок, урон (2.4c) ----------


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


def kagune_gate_chance(
    defender_dex_speed: float, attacker_dex_speed: float
) -> float:
    """Шанс защищающегося успеть поднять кагуне для защиты этого удара -
    см. BATTLE_ENGINE.md 2.4c шаг 2. При равных статах - ровно половина."""

    if attacker_dex_speed <= 0:
        return 100.0
    return min(
        100.0,
        BATTLE_CONFIG.kagune_gate_base_percent
        * defender_dex_speed
        / attacker_dex_speed,
    )


def resolve_block_percent(
    kagune_up: bool,
    attack_type: AttackType,
    attacker: EffectiveStats,
    defender: EffectiveStats,
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
    attack_type: AttackType, attacker: EffectiveStats, rng: random.Random
) -> float:
    variance = rng.uniform(
        BATTLE_CONFIG.damage_variance_min, BATTLE_CONFIG.damage_variance_max
    )
    if attack_type is AttackType.PHYSICAL:
        return variance * attacker.strength
    return variance * (attacker.strength + attacker.kagune_strength)


@dataclass(frozen=True)
class HitResult:
    landed: bool
    attack_type: Optional[AttackType] = None
    kagune_up: Optional[bool] = None
    block_percent: float = 0.0
    damage: float = 0.0
    # Сами использованные шансы (не только исход броска) - production-код их
    # не читает, нужны только для трассировки/отладочных логов (см.
    # scripts/battle_log_demo.py), поэтому храним, а не пересчитываем заново.
    dodge_chance_used: float = 0.0
    gate_chance_used: float = 0.0
    physical_chance_used: float = 0.0


def resolve_hit(
    attacker: EffectiveStats,
    defender: EffectiveStats,
    attacker_physical_streak: int,
    rng: random.Random = _default_rng,
) -> "tuple[HitResult, int]":
    """Один честный удар атакующего по защищающемуся - полная цепочка из
    BATTLE_ENGINE.md 2.4c: уклонение -> гейт кагуне-защиты -> тип атаки ->
    блок -> урон.

    `attacker_physical_streak` - сколько физических ударов подряд (за весь
    бой, не за раунд) этот боец уже нанёс, см. attack_type_chance. Функция
    возвращает (результат_удара, ОБНОВЛЁННЫЙ streak) - вызывающий код
    обязан передать это значение в следующий вызов resolve_hit для этого
    же бойца, иначе счётчик не будет работать между ударами/раундами."""

    dodge = dodge_chance(defender.dexterity, attacker.dexterity)
    if rng.random() * 100.0 < dodge:
        return HitResult(landed=False, dodge_chance_used=dodge), attacker_physical_streak

    gate = kagune_gate_chance(
        defender.dexterity + defender.speed, attacker.dexterity + attacker.speed
    )
    kagune_up = rng.random() * 100.0 < gate

    physical_chance = attack_type_chance(attacker_physical_streak)
    if rng.random() * 100.0 < physical_chance:
        attack_type = AttackType.PHYSICAL
        new_streak = attacker_physical_streak + 1
    else:
        attack_type = AttackType.KAGUNE
        new_streak = attacker_physical_streak  # кагуне-удар счётчик не двигает

    block_percent = resolve_block_percent(kagune_up, attack_type, attacker, defender, rng)
    damage = raw_damage(attack_type, attacker, rng) * (1 - block_percent / 100.0)

    hit = HitResult(
        landed=True,
        attack_type=attack_type,
        kagune_up=kagune_up,
        block_percent=block_percent,
        damage=damage,
        dodge_chance_used=dodge,
        gate_chance_used=gate,
        physical_chance_used=physical_chance,
    )
    return hit, new_streak


# --- Раунд и весь бой (часть 0, 2.1, 2.6) ----------------------------------


@dataclass(frozen=True)
class RoundResult:
    round_number: int
    hits_by_a: List[HitResult]
    hits_by_b: List[HitResult]
    damage_to_a: float
    damage_to_b: float


def simulate_round(
    round_number: int,
    stats_a: EffectiveStats,
    stats_b: EffectiveStats,
    streak_a: int = 0,
    streak_b: int = 0,
    rng: random.Random = _default_rng,
) -> "tuple[RoundResult, int, int]":
    """Оба бойца действуют одновременно (2.1) - порядок вычисления здесь
    чисто технический, на исход не влияет.

    `streak_a`/`streak_b` - счётчик физических ударов подряд для КАЖДОГО
    бойца (см. attack_type_chance) - переживает раунд, поэтому функция
    возвращает их обновлённые значения вместе с самим RoundResult; вызывающий
    код (simulate_battle) обязан передать их в следующий вызов."""

    hit_count_a, hit_count_b = resolve_hit_count(stats_a.speed, stats_b.speed, rng)

    hits_by_a: List[HitResult] = []
    for _ in range(hit_count_a):
        hit, streak_a = resolve_hit(stats_a, stats_b, streak_a, rng)
        hits_by_a.append(hit)

    hits_by_b: List[HitResult] = []
    for _ in range(hit_count_b):
        hit, streak_b = resolve_hit(stats_b, stats_a, streak_b, rng)
        hits_by_b.append(hit)

    result = RoundResult(
        round_number=round_number,
        hits_by_a=hits_by_a,
        hits_by_b=hits_by_b,
        damage_to_a=sum(hit.damage for hit in hits_by_b),
        damage_to_b=sum(hit.damage for hit in hits_by_a),
    )
    return result, streak_a, streak_b


@dataclass(frozen=True)
class BattleResult:
    rounds: List[RoundResult]
    winner: Optional[str]  # "a" | "b" | None (истинная ничья, тай-брейк не спас)
    ended_naturally: bool  # True - кто-то дошёл до 0 HP раньше MAX_ROUNDS
    final_hp_a: float
    final_hp_b: float
    stats_a: EffectiveStats
    stats_b: EffectiveStats


def simulate_battle(
    fighter_a: FighterSnapshot,
    fighter_b: FighterSnapshot,
    rng: random.Random = _default_rng,
    max_rounds: Optional[int] = None,
) -> BattleResult:
    """Весь бой раунд за раундом, см. BATTLE_ENGINE.md часть 0/2.6.
    Поднимает InvalidBattleStatsError (2.4d), если у кого-то из бойцов
    невозможные статы - вызывающий код обязан отменить бой, не пытаться
    досчитать с мусорными числами."""

    validate_snapshot(fighter_a)
    validate_snapshot(fighter_b)

    stats_a = compute_effective_stats(fighter_a)
    stats_b = compute_effective_stats(fighter_b)

    rounds_cap = max_rounds if max_rounds is not None else BATTLE_CONFIG.max_rounds

    hp_a, hp_b = stats_a.health, stats_b.health
    rounds: List[RoundResult] = []
    hp_a_before_last, hp_b_before_last = hp_a, hp_b
    # Счётчик "физических ударов подряд" на бойца (см. attack_type_chance) -
    # переживает раунды, обнуляется только один раз в начале боя.
    streak_a, streak_b = 0, 0

    for round_number in range(1, rounds_cap + 1):
        hp_a_before_last, hp_b_before_last = hp_a, hp_b

        result, streak_a, streak_b = simulate_round(
            round_number, stats_a, stats_b, streak_a, streak_b, rng
        )
        hp_a = max(0.0, hp_a - result.damage_to_a)
        hp_b = max(0.0, hp_b - result.damage_to_b)
        rounds.append(result)

        if hp_a <= 0 or hp_b <= 0:
            break

    ended_naturally = hp_a <= 0 or hp_b <= 0

    if hp_a <= 0 and hp_b <= 0:
        # 2.6 - одновременный обоюдный нокаут, тай-брейк не был решён явно
        # в доке. Рабочее правило: побеждает тот, у кого HP ДО последнего
        # обмена было выше; если и тут ничья - настоящая ничья (None).
        if hp_a_before_last > hp_b_before_last:
            winner: Optional[str] = "a"
        elif hp_b_before_last > hp_a_before_last:
            winner = "b"
        else:
            winner = None
    elif hp_a <= 0:
        winner = "b"
    elif hp_b <= 0:
        winner = "a"
    else:
        # MAX_ROUNDS кончились без естественного конца - решает остаток HP.
        if hp_a > hp_b:
            winner = "a"
        elif hp_b > hp_a:
            winner = "b"
        else:
            winner = None

    return BattleResult(
        rounds=rounds,
        winner=winner,
        ended_naturally=ended_naturally,
        final_hp_a=hp_a,
        final_hp_b=hp_b,
        stats_a=stats_a,
        stats_b=stats_b,
    )


__all__ = [
    "InvalidBattleStatsError",
    "AttackType",
    "KAGUNE_TYPE_MULTIPLIERS",
    "KAGUNE_TYPE_PRIORITY_STAT",
    "resolve_kagune_multiplier",
    "FighterSnapshot",
    "EffectiveStats",
    "validate_snapshot",
    "compute_effective_stats",
    "dodge_chance",
    "extra_hit_percent",
    "resolve_hit_chain",
    "resolve_hit_count",
    "attack_type_chance",
    "kagune_gate_chance",
    "resolve_block_percent",
    "raw_damage",
    "HitResult",
    "resolve_hit",
    "RoundResult",
    "simulate_round",
    "BattleResult",
    "simulate_battle",
]
