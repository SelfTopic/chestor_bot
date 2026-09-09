import random

import pytest

from src.bot.types import KaguneType
from src.bot.utils.battle_calculate import (
    AttackType,
    FighterSnapshot,
    InvalidBattleStatsError,
    compute_effective_stats,
    dodge_chance,
    extra_hit_percent,
    kagune_gate_chance,
    resolve_block_percent,
    resolve_hit_chain,
    resolve_hit_count,
    resolve_kagune_multiplier,
    simulate_battle,
    validate_snapshot,
)


def make_fighter(**overrides) -> FighterSnapshot:
    defaults = dict(
        id=1,
        name="Тест",
        strength=100,
        dexterity=100,
        regeneration=100,
        speed=100,
        health=100,
        hunger=100,
        is_kakuja=False,
        kagune_strength={},
    )
    defaults.update(overrides)
    return FighterSnapshot(**defaults)


# --- Уклонение (2.3) --------------------------------------------------------


def test_dodge_chance_equal_dexterity_is_symmetric():
    a = dodge_chance(defender_dexterity=100, attacker_dexterity=100)
    b = dodge_chance(defender_dexterity=100, attacker_dexterity=100)
    assert a == b


def test_dodge_chance_floor_and_ceiling():
    # dexterity=0 - пол 5%, а не 0 (base(0) = 5 + 0 = 5 ровно).
    assert dodge_chance(defender_dexterity=0, attacker_dexterity=0) == pytest.approx(5.0)
    # Огромный перевес защищающегося - потолок 95%, не выше.
    chance = dodge_chance(defender_dexterity=100_000, attacker_dexterity=1)
    assert chance == pytest.approx(95.0)


def test_dodge_chance_weaker_gets_base_stronger_gets_scaled():
    weaker = dodge_chance(defender_dexterity=100, attacker_dexterity=200)
    stronger = dodge_chance(defender_dexterity=200, attacker_dexterity=100)
    assert stronger > weaker


# --- Лишний удар от speed (1.4) --------------------------------------------


def test_extra_hit_percent_matches_worked_examples_from_battle_engine_doc():
    # speed 10 vs 20 -> медленный 50%, быстрый 100% (BATTLE_ENGINE.md 1.4)
    assert extra_hit_percent(speed_defender=20, speed_attacker=10) == pytest.approx(50.0)
    assert extra_hit_percent(speed_defender=10, speed_attacker=20) == pytest.approx(100.0)

    # speed 190 vs 200 -> медленный 5%, быстрый 10%
    assert extra_hit_percent(speed_defender=200, speed_attacker=190) == pytest.approx(5.0)
    assert extra_hit_percent(speed_defender=190, speed_attacker=200) == pytest.approx(10.0)


def test_extra_hit_percent_equal_speed_is_zero():
    assert extra_hit_percent(speed_defender=100, speed_attacker=100) == 0.0


def test_extra_hit_percent_can_exceed_100_for_large_gaps():
    # speed 10 против 100: diff/max=0.9 -> у быстрого 180%, без клэмпа.
    pct = extra_hit_percent(speed_defender=10, speed_attacker=100)
    assert pct == pytest.approx(180.0)


def test_resolve_hit_chain_converts_over_100_into_guaranteed_plus_roll():
    rng = random.Random(1)
    # 180% -> 1 гарантированный удар + бросок на 80% для второго лишнего.
    always_hits = resolve_hit_chain(180.0, random.Random(0))  # почти любой сид даст >=1
    assert always_hits >= 1

    # 0% -> никогда никакого лишнего удара, при любом сиде.
    for seed in range(20):
        assert resolve_hit_chain(0.0, random.Random(seed)) == 0

    # ровно 100% -> гарантированно 1 лишний, без вероятностного довеска.
    assert resolve_hit_chain(100.0, rng) == 1


def test_resolve_hit_count_faster_fighter_gets_more_hits_on_average():
    rng = random.Random(42)
    totals_fast = 0
    totals_slow = 0
    trials = 500
    for _ in range(trials):
        hits_fast, hits_slow = resolve_hit_count(200, 100, rng)
        totals_fast += hits_fast
        totals_slow += hits_slow
    assert totals_fast > totals_slow


# --- Гейт кагуне-защиты (2.4c шаг 2) ----------------------------------------


def test_kagune_gate_chance_equal_stats_is_half():
    assert kagune_gate_chance(100, 100) == pytest.approx(50.0)


def test_kagune_gate_chance_double_advantage_is_certain():
    assert kagune_gate_chance(200, 100) == pytest.approx(100.0)


def test_kagune_gate_chance_clamped_at_100():
    assert kagune_gate_chance(1000, 10) == pytest.approx(100.0)


# --- Множители типов кагуне: приоритет + min()-fallback ---------------------


def test_kagune_multiplier_no_owned_types_is_neutral():
    assert resolve_kagune_multiplier("speed", []) == 1.0


def test_kagune_multiplier_priority_owner_wins_over_bigger_secondary_value():
    # Укаку(1.8 speed, приоритет) + Бикаку(1.4 speed, не приоритет) -> 1.8,
    # см. BATTLE_ENGINE.md "Итог" (пример Укаку+Бикаку).
    owned = [KaguneType.UKAKU, KaguneType.BIKAKU]
    assert resolve_kagune_multiplier("speed", owned) == pytest.approx(1.8)


def test_kagune_multiplier_falls_back_to_min_without_priority_owner():
    # Бикаку(1.4 speed) + Ринкаку(1.5 speed), ни один не хозяин speed
    # (хозяин - Укаку, его нет) -> min(1.4, 1.5) = 1.4.
    owned = [KaguneType.BIKAKU, KaguneType.RINKAKU]
    assert resolve_kagune_multiplier("speed", owned) == pytest.approx(1.4)


# --- Полная цепочка эффективных статов --------------------------------------


def test_effective_stats_no_kagune_no_kakuja_full_hunger_is_unchanged():
    fighter = make_fighter(hunger=100, is_kakuja=False, kagune_strength={})
    stats = compute_effective_stats(fighter)
    assert stats.strength == pytest.approx(100)
    assert stats.dexterity == pytest.approx(100)
    assert stats.regeneration == pytest.approx(100)
    assert stats.speed == pytest.approx(100)
    assert stats.health == pytest.approx(100)
    assert stats.kagune_strength == pytest.approx(0)


def test_effective_health_can_exceed_vacuum_max_health_when_kagune_boosts_it():
    # Бикаку 1.4x health - гуль 1000/1000 может честно начать бой с 1400
    # эффективного HP, см. BATTLE_ENGINE.md 1.3.
    fighter = make_fighter(
        health=1000, kagune_strength={KaguneType.BIKAKU: 100}, hunger=100
    )
    stats = compute_effective_stats(fighter)
    assert stats.health == pytest.approx(1400)


def test_kakuja_multiplies_on_top_of_kagune_type_multiplier():
    fighter_no_kakuja = make_fighter(
        speed=100, kagune_strength={KaguneType.UKAKU: 0}, is_kakuja=False
    )
    fighter_kakuja = make_fighter(
        speed=100, kagune_strength={KaguneType.UKAKU: 0}, is_kakuja=True
    )
    stats_no = compute_effective_stats(fighter_no_kakuja)
    stats_yes = compute_effective_stats(fighter_kakuja)
    # 100 * 1.8 (Укаку speed) * 3 (какудж) = 540
    assert stats_yes.speed == pytest.approx(stats_no.speed * 3)
    assert stats_yes.speed == pytest.approx(540)


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
    fighter = make_fighter(**overrides)
    with pytest.raises(InvalidBattleStatsError):
        validate_snapshot(fighter)


def test_validate_snapshot_accepts_normal_fighter():
    validate_snapshot(make_fighter())  # не должно кидать


# --- Блок (2.4c) - направление и границы ------------------------------------


def test_block_kagune_vs_kagune_full_damage_when_defender_weaker():
    rng = random.Random(0)
    attacker = compute_effective_stats(
        make_fighter(kagune_strength={KaguneType.RINKAKU: 200})
    )
    defender = compute_effective_stats(
        make_fighter(kagune_strength={KaguneType.RINKAKU: 50})
    )
    block = resolve_block_percent(True, AttackType.KAGUNE, attacker, defender, rng)
    assert block == 0.0


def test_block_kagune_vs_kagune_modest_when_defender_not_weaker():
    rng = random.Random(0)
    attacker = compute_effective_stats(
        make_fighter(kagune_strength={KaguneType.RINKAKU: 50})
    )
    defender = compute_effective_stats(
        make_fighter(kagune_strength={KaguneType.RINKAKU: 200})
    )
    block = resolve_block_percent(True, AttackType.KAGUNE, attacker, defender, rng)
    assert 10.0 <= block <= 20.0


def test_block_no_kagune_defense_against_kagune_attack_is_always_zero():
    rng = random.Random(0)
    attacker = compute_effective_stats(make_fighter())
    defender = compute_effective_stats(make_fighter())
    block = resolve_block_percent(False, AttackType.KAGUNE, attacker, defender, rng)
    assert block == 0.0


# --- Весь бой (часть 0, 2.6) -------------------------------------------------


def test_simulate_battle_never_exceeds_max_rounds():
    # Почти зеркальные бойцы - бой скорее дотянет до предела раундов.
    a = make_fighter(id=1, name="A")
    b = make_fighter(id=2, name="B")
    result = simulate_battle(a, b, rng=random.Random(7), max_rounds=10)
    assert len(result.rounds) <= 10


def test_simulate_battle_ends_naturally_when_hp_hits_zero():
    strong = make_fighter(id=1, name="Сильный", strength=100_000, health=100_000)
    weak = make_fighter(id=2, name="Слабый", strength=1, health=1)
    result = simulate_battle(strong, weak, rng=random.Random(3), max_rounds=100)
    assert result.ended_naturally
    assert result.winner == "a"
    assert len(result.rounds) < 100


def test_simulate_battle_raises_on_invalid_fighter():
    broken = make_fighter(dexterity=0)
    ok = make_fighter()
    with pytest.raises(InvalidBattleStatsError):
        simulate_battle(broken, ok)


def test_simulate_battle_is_deterministic_with_same_seed():
    a = make_fighter(id=1, name="A")
    b = make_fighter(id=2, name="B")
    result1 = simulate_battle(a, b, rng=random.Random(123))
    result2 = simulate_battle(a, b, rng=random.Random(123))
    assert result1.winner == result2.winner
    assert result1.final_hp_a == pytest.approx(result2.final_hp_a)
    assert result1.final_hp_b == pytest.approx(result2.final_hp_b)
    assert len(result1.rounds) == len(result2.rounds)
