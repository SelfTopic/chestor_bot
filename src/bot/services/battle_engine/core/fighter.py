"""
Снапшот бойца, эффективные (боевые) статы и сам класс Fighter - объект,
несущий состояние ОДНОГО боя (HP, streak физических ударов, состояние
регенерации). Раньше (battle_calculate.py) всё это было отдельными
переменными (hp_a, streak_a, regen_state_a, ...), вручную протаскиваемыми
через параметры функций - Fighter существует именно для того, чтобы
убрать эту "нитку из шести переменных" и держать состояние там, где ему
место: в объекте.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List

from ....game_configs import BATTLE_CONFIG, PASSIVE_STATS_CONFIG
from ....types import KaguneType
from ....utils.regen_calculate import get_hunger_tier
from .actions import RoundActionType
from .errors import InvalidBattleStatsError
from .formulas import compress_stat_advantage, regen_proc_chance

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

# "Растущие" статы под голодом (получают rising_multiplier тира) -
# strength и kagune_strength, см. BATTLE_DESIGN.md "Множители голода" -
# зашито явно per-call в compute_effective_stats (is_rising=True/False),
# не через отдельную таблицу. Всё остальное боевое - "падающее"; health
# сюда отнесён по аналогии с dexterity/regeneration/speed ("выносливость
# слабеет при голоде") - явно нигде не решалось, рабочее предположение.


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
    kagune_strength = fighter.total_kagune_strength * tier.rising_multiplier * kakuja_mult

    return EffectiveStats(
        strength=strength,
        dexterity=dexterity,
        regeneration=regeneration,
        speed=speed,
        health=health,
        kagune_strength=kagune_strength,
    )


# --- Fighter - боец с состоянием на весь бой -------------------------------


class Fighter:
    """Обёртка над FighterSnapshot, несущая состояние ОДНОГО боя: текущий
    HP, streak физических ударов подряд (attack_type_chance), состояние
    регенерации. Валидирует снапшот в конструкторе - ошибка ловится
    максимально рано, до создания Battle вообще."""

    def __init__(self, snapshot: FighterSnapshot) -> None:
        validate_snapshot(snapshot)

        self.snapshot = snapshot
        self.stats: EffectiveStats = compute_effective_stats(snapshot)
        self.current_hp: float = self.stats.health
        self.physical_streak: int = 0
        self.regen_guaranteed_used: bool = False
        self.regen_roll_used: bool = False

    @property
    def id(self) -> int:
        return self.snapshot.id

    @property
    def name(self) -> str:
        return self.snapshot.name

    @property
    def is_defeated(self) -> bool:
        return self.current_hp <= 0

    def take_damage(self, amount: float) -> None:
        self.current_hp = max(0.0, self.current_hp - amount)

    def is_critical(self) -> bool:
        """Ниже критического порога (BATTLE_CONFIG.critical_health_percent
        от СТАРТОВОГО HP этого боя), но ещё не побеждён - см.
        REGENERATION.md. Уже проигравший (hp<=0) не считается критическим
        - его не лечат, 2.6 сильнее."""

        if self.current_hp <= 0:
            return False
        threshold = self.stats.health * (BATTLE_CONFIG.critical_health_percent / 100.0)
        return self.current_hp < threshold

    def decide_action(self, opponent: "Fighter", rng: random.Random) -> RoundActionType:
        """ОСНОВНОЕ действие на раунд - Attack или Regen (Defense/Idle
        зарезервированы, см. actions.py). Мутирует regen_guaranteed_used/
        regen_roll_used как побочный эффект - см. REGENERATION.md
        ("проверка тратится только один раз за бой")."""

        if not self.is_critical():
            return RoundActionType.ATTACK

        if not self.regen_guaranteed_used:
            self.regen_guaranteed_used = True
            return RoundActionType.REGEN

        if not self.regen_roll_used:
            self.regen_roll_used = True
            chance = regen_proc_chance(self.stats.regeneration, opponent.stats.regeneration)
            if rng.random() * 100.0 < chance:
                return RoundActionType.REGEN

        return RoundActionType.ATTACK

    def apply_heal(self, opponent: "Fighter", rng: random.Random) -> float:
        """Вызывается ТОЛЬКО когда decide_action уже вернул REGEN в этом
        же раунде. Лечит на regen_heal_variance от эффективной
        регенерации, клэмп по стартовому HP боя. Возвращает сколько
        реально вылечено (может быть меньше "сырого" heal из-за клэмпа).

        Сила хила сжимается против чужой регенерации (compress_stat_
        advantage) - без этого абсолютная величина хила оставалась
        ЕДИНСТВЕННЫМ полностью несжатым каналом "кривой перевеса силы"
        (regen_proc_chance сжимал только ВЕРОЯТНОСТЬ второго прока, а не
        то, сколько реально лечится за один прок) - см. чат, симуляция
        подтвердила: при зафиксированной равной регенерации кривая ложится
        на цель, при масштабируемой вместе с остальными статами - нет."""

        variance = rng.uniform(
            BATTLE_CONFIG.regen_heal_variance_min, BATTLE_CONFIG.regen_heal_variance_max
        )
        effective_regeneration = compress_stat_advantage(
            self.stats.regeneration, opponent.stats.regeneration
        )
        heal = variance * effective_regeneration
        new_hp = min(self.stats.health, self.current_hp + heal)
        healed = new_hp - self.current_hp
        self.current_hp = new_hp
        return healed


__all__ = [
    "KAGUNE_TYPE_MULTIPLIERS",
    "KAGUNE_TYPE_PRIORITY_STAT",
    "resolve_kagune_multiplier",
    "FighterSnapshot",
    "EffectiveStats",
    "validate_snapshot",
    "compute_effective_stats",
    "Fighter",
]
