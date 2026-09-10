from typing import Dict, Optional

import pytest

from src.bot.services.battle_engine.core.errors import InvalidBattleStatsError
from src.bot.services.battle_engine.core.fighter import (
    Fighter,
    FighterSnapshot,
    compute_effective_stats,
    resolve_kagune_multiplier,
    validate_snapshot,
)
from src.bot.types import KaguneType


def make_snapshot(
    id: int = 1,
    name: str = "Тест",
    strength: int = 100,
    dexterity: int = 100,
    regeneration: int = 100,
    speed: int = 100,
    health: int = 100,
    hunger: int = 100,
    is_kakuja: bool = False,
    kagune_strength: Optional[Dict[KaguneType, int]] = None,
) -> FighterSnapshot:
    return FighterSnapshot(
        id=id,
        name=name,
        strength=strength,
        dexterity=dexterity,
        regeneration=regeneration,
        speed=speed,
        health=health,
        hunger=hunger,
        is_kakuja=is_kakuja,
        kagune_strength=kagune_strength or {},
    )


# --- Множители типов кагуне: приоритет + min()-fallback ---------------------


def test_kagune_multiplier_no_owned_types_is_neutral():
    assert resolve_kagune_multiplier("speed", []) == 1.0


def test_kagune_multiplier_priority_owner_wins_over_bigger_secondary_value():
    # Укаку(1.8 speed, приоритет) + Бикаку(1.4 speed, не приоритет) -> 1.8
    owned = [KaguneType.UKAKU, KaguneType.BIKAKU]
    assert resolve_kagune_multiplier("speed", owned) == pytest.approx(1.8)


def test_kagune_multiplier_falls_back_to_min_without_priority_owner():
    # Бикаку(1.4 speed) + Ринкаку(1.5 speed), ни один не хозяин speed
    # (хозяин - Укаку, его нет) -> min(1.4, 1.5) = 1.4
    owned = [KaguneType.BIKAKU, KaguneType.RINKAKU]
    assert resolve_kagune_multiplier("speed", owned) == pytest.approx(1.4)


# --- Полная цепочка эффективных статов --------------------------------------


def test_effective_stats_no_kagune_no_kakuja_full_hunger_is_unchanged():
    snapshot = make_snapshot(hunger=100, is_kakuja=False, kagune_strength={})
    stats = compute_effective_stats(snapshot)
    assert stats.strength == pytest.approx(100)
    assert stats.dexterity == pytest.approx(100)
    assert stats.regeneration == pytest.approx(100)
    assert stats.speed == pytest.approx(100)
    assert stats.health == pytest.approx(100)
    assert stats.kagune_strength == pytest.approx(0)


def test_effective_health_can_exceed_vacuum_max_health_when_kagune_boosts_it():
    # Бикаку 1.4x health - гуль 1000/1000 может честно начать бой с 1400
    # эффективного HP, см. BATTLE_ENGINE.md 1.3.
    snapshot = make_snapshot(health=1000, kagune_strength={KaguneType.BIKAKU: 100}, hunger=100)
    stats = compute_effective_stats(snapshot)
    assert stats.health == pytest.approx(1400)


def test_kakuja_multiplies_on_top_of_kagune_type_multiplier():
    no_kakuja = compute_effective_stats(
        make_snapshot(speed=100, kagune_strength={KaguneType.UKAKU: 0}, is_kakuja=False)
    )
    with_kakuja = compute_effective_stats(
        make_snapshot(speed=100, kagune_strength={KaguneType.UKAKU: 0}, is_kakuja=True)
    )
    # 100 * 1.8 (Укаку speed) * 3 (какудж) = 540
    assert with_kakuja.speed == pytest.approx(no_kakuja.speed * 3)
    assert with_kakuja.speed == pytest.approx(540)


# --- Валидация (2.4d) -------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"dexterity": 0},
        {"speed": 0},
        {"dexterity": -1},
        {"health": 0},
        {"hunger": 101},
        {"hunger": -1},
        {"kagune_strength": {KaguneType.UKAKU: -5}},
    ],
)
def test_validate_snapshot_rejects_impossible_stats(overrides):
    snapshot = make_snapshot(**overrides)
    with pytest.raises(InvalidBattleStatsError):
        validate_snapshot(snapshot)


def test_validate_snapshot_accepts_normal_fighter():
    validate_snapshot(make_snapshot())  # не должно кидать


# --- Fighter - объект с состоянием ------------------------------------------


def test_fighter_construction_computes_effective_stats_and_starting_hp():
    fighter = Fighter(make_snapshot(health=100))
    assert fighter.current_hp == pytest.approx(fighter.stats.health)
    assert fighter.physical_streak == 0
    assert not fighter.is_defeated


def test_fighter_construction_raises_on_invalid_snapshot():
    with pytest.raises(InvalidBattleStatsError):
        Fighter(make_snapshot(dexterity=0))


def test_fighter_take_damage_clamps_at_zero():
    fighter = Fighter(make_snapshot(health=100))
    fighter.take_damage(1000)
    assert fighter.current_hp == 0.0
    assert fighter.is_defeated


def test_fighter_is_critical_below_threshold_only_while_alive():
    fighter = Fighter(make_snapshot(health=100))
    assert not fighter.is_critical()  # полное HP

    fighter.take_damage(95)  # 5 HP - ниже 10%
    assert fighter.is_critical()

    fighter.take_damage(1000)  # добивание - hp<=0
    assert not fighter.is_critical()  # уже проигравший не "критический"
