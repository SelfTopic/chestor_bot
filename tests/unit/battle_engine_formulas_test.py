import random

import pytest

from src.bot.game_configs import BATTLE_CONFIG
from src.bot.services.battle_engine.core.fighter import EffectiveStats
from src.bot.services.battle_engine.core.formulas import (
    AttackType,
    attack_type_chance,
    dodge_chance,
    extra_hit_percent,
    kagune_gate_chance,
    raw_damage,
    raw_fast_attack_damage,
    regen_proc_chance,
    resolve_block_percent,
    resolve_extra_hit_counts,
    resolve_hit_chain,
)


def make_stats(**overrides) -> EffectiveStats:
    defaults = dict(
        strength=100.0,
        dexterity=100.0,
        regeneration=100.0,
        speed=100.0,
        health=100.0,
        kagune_strength=0.0,
    )
    defaults.update(overrides)
    return EffectiveStats(**defaults)


# --- Уклонение (2.3) --------------------------------------------------------


def test_dodge_chance_equal_dexterity_is_symmetric():
    a = dodge_chance(defender_dexterity=100, attacker_dexterity=100)
    b = dodge_chance(defender_dexterity=100, attacker_dexterity=100)
    assert a == b


def test_dodge_chance_floor_and_ceiling(monkeypatch: pytest.MonkeyPatch):
    assert dodge_chance(defender_dexterity=0, attacker_dexterity=0) == pytest.approx(5.0)
    # exponent=1.0 - проверяем, что клэмп на потолке вообще существует и
    # работает, НЕЗАВИСИМО от текущей калибровки stat_sensitivity_exponent
    # (0.03, см. game_configs.py) - иначе тест ломался бы каждый раз, когда
    # экспонент перекалибровывают под новую целевую кривую.
    monkeypatch.setattr(BATTLE_CONFIG, "stat_sensitivity_exponent", 1.0)
    chance = dodge_chance(defender_dexterity=100_000, attacker_dexterity=1)
    assert chance == pytest.approx(95.0)


def test_dodge_chance_weaker_gets_base_stronger_gets_scaled():
    weaker = dodge_chance(defender_dexterity=100, attacker_dexterity=200)
    stronger = dodge_chance(defender_dexterity=200, attacker_dexterity=100)
    assert stronger > weaker


# --- Лишний удар от speed (1.4) --------------------------------------------


def test_extra_hit_percent_matches_worked_examples_from_battle_engine_doc(
    monkeypatch: pytest.MonkeyPatch,
):
    # Значения из BATTLE_ENGINE.md 1.4 (50/100, 5/10) относятся к "сырому"
    # diff_ratio - exponent=1.0 (без сжатия под целевую кривую перевеса
    # силы, см. game_configs.py) воспроизводит их буквально.
    monkeypatch.setattr(BATTLE_CONFIG, "stat_sensitivity_exponent", 1.0)

    # speed 10 vs 20 -> медленный 50%, быстрый 100% (BATTLE_ENGINE.md 1.4)
    assert extra_hit_percent(speed_defender=20, speed_attacker=10) == pytest.approx(50.0)
    assert extra_hit_percent(speed_defender=10, speed_attacker=20) == pytest.approx(100.0)

    # speed 190 vs 200 -> медленный 5%, быстрый 10%
    assert extra_hit_percent(speed_defender=200, speed_attacker=190) == pytest.approx(5.0)
    assert extra_hit_percent(speed_defender=190, speed_attacker=200) == pytest.approx(10.0)


def test_extra_hit_percent_faster_side_always_gets_double_the_slower_side():
    # Это должно оставаться верным при ЛЮБОЙ калибровке
    # stat_sensitivity_exponent - сжатие применяется к одному и тому же
    # diff_ratio с обеих сторон, множители 200/100 не зависят от неё.
    slower = extra_hit_percent(speed_defender=200, speed_attacker=100)
    faster = extra_hit_percent(speed_defender=100, speed_attacker=200)
    assert faster == pytest.approx(slower * 2)


def test_extra_hit_percent_equal_speed_is_zero():
    assert extra_hit_percent(speed_defender=100, speed_attacker=100) == 0.0


def test_extra_hit_percent_can_exceed_100_for_large_gaps():
    # Сама возможность превышения 100% (и, соответственно, гарантированные
    # удары в resolve_hit_chain) не зависит от stat_sensitivity_exponent -
    # при достаточно большом разрыве всегда превысит 100%, просто порог
    # разный при разных калибровках.
    pct = extra_hit_percent(speed_defender=1, speed_attacker=10**12)
    assert pct > 100.0


def test_resolve_hit_chain_converts_over_100_into_guaranteed_plus_roll():
    rng = random.Random(1)
    always_hits = resolve_hit_chain(180.0, random.Random(0))
    assert always_hits >= 1

    for seed in range(20):
        assert resolve_hit_chain(0.0, random.Random(seed)) == 0

    assert resolve_hit_chain(100.0, rng) == 1


def test_resolve_extra_hit_counts_has_no_guaranteed_plus_one():
    # В отличие от старого resolve_hit_count - при равной скорости обе
    # стороны получают 0 БОНУСНЫХ ударов, а не гарантированный "+1" каждой.
    extra_a, extra_b = resolve_extra_hit_counts(100, 100, random.Random(0))
    assert extra_a == 0
    assert extra_b == 0


def test_resolve_extra_hit_counts_faster_fighter_gets_more_bonus_hits_on_average():
    rng = random.Random(42)
    totals_fast = 0
    totals_slow = 0
    trials = 500
    for _ in range(trials):
        extra_fast, extra_slow = resolve_extra_hit_counts(200, 100, rng)
        totals_fast += extra_fast
        totals_slow += extra_slow
    assert totals_fast > totals_slow


# --- Гейт кагуне-защиты (2.4c шаг 2) ----------------------------------------


def test_kagune_gate_chance_equal_stats_is_half():
    assert kagune_gate_chance(100, 100) == pytest.approx(50.0)


def test_kagune_gate_chance_double_advantage_is_no_longer_certain():
    # Раньше 2x перевес давал ровно 100% (гарантию) - это была именно та
    # "кривая перевеса силы", которую сжали _compress_ratio (см. чат).
    # Теперь 2x даёт заметное, но не абсолютное преимущество.
    chance = kagune_gate_chance(200, 100)
    assert 50.0 < chance < 100.0


def test_kagune_gate_chance_clamped_at_100(monkeypatch: pytest.MonkeyPatch):
    # exponent=1.0 - клэмп проверяем отдельно от текущей калибровки
    # stat_sensitivity_exponent (см. test_dodge_chance_floor_and_ceiling).
    monkeypatch.setattr(BATTLE_CONFIG, "stat_sensitivity_exponent", 1.0)
    assert kagune_gate_chance(1000, 10) == pytest.approx(100.0)


# --- Тип атаки: первый удар физический, дальше -10% за физический удар -----


def test_attack_type_chance_first_hit_is_guaranteed_physical():
    assert attack_type_chance(0) == 100.0


def test_attack_type_chance_decays_only_by_configured_step():
    assert attack_type_chance(1) == pytest.approx(90.0)
    assert attack_type_chance(3) == pytest.approx(70.0)


def test_attack_type_chance_floors_at_zero_not_negative():
    assert attack_type_chance(15) == 0.0


# --- Регенерация в бою -------------------------------------------------------


def test_regen_proc_chance_equal_regeneration_is_zero():
    assert regen_proc_chance(100, 100) == 0.0


def test_regen_proc_chance_higher_regen_gets_double_the_lower_side():
    weaker = regen_proc_chance(50, 100)
    stronger = regen_proc_chance(100, 50)
    assert stronger == pytest.approx(weaker * 2)


# --- Блок (2.4c) - направление и границы ------------------------------------


def test_block_kagune_vs_kagune_full_damage_when_defender_weaker():
    rng = random.Random(0)
    attacker = make_stats(kagune_strength=200)
    defender = make_stats(kagune_strength=50)
    block = resolve_block_percent(True, AttackType.KAGUNE, attacker, defender, rng)
    assert block == 0.0


def test_block_kagune_vs_kagune_modest_when_defender_not_weaker():
    rng = random.Random(0)
    attacker = make_stats(kagune_strength=50)
    defender = make_stats(kagune_strength=200)
    block = resolve_block_percent(True, AttackType.KAGUNE, attacker, defender, rng)
    assert 10.0 <= block <= 20.0


def test_block_no_kagune_defense_against_kagune_attack_is_always_zero():
    rng = random.Random(0)
    attacker = make_stats()
    defender = make_stats()
    block = resolve_block_percent(False, AttackType.KAGUNE, attacker, defender, rng)
    assert block == 0.0


def test_raw_damage_kagune_attack_includes_kagune_strength():
    attacker = make_stats(strength=100, kagune_strength=50)
    defender = make_stats(strength=100)
    physical = raw_damage(AttackType.PHYSICAL, attacker, defender, random.Random(0))
    kagune = raw_damage(AttackType.KAGUNE, attacker, defender, random.Random(0))
    assert kagune > physical


def test_fast_attack_damage_is_weaker_than_a_full_attack_on_average():
    # "Мелкие однообразные атаки" (лор Укаку) - FastAttack не может быть
    # такой же силы, как обычная атака, иначе чистый вклад в speed сносил
    # бы 3-4 полных удара за раунд.
    attacker = make_stats(strength=100)
    defender = make_stats(strength=100)
    trials = 2000
    full_total = sum(
        raw_damage(AttackType.PHYSICAL, attacker, defender, random.Random(seed))
        for seed in range(trials)
    )
    fast_total = sum(
        raw_fast_attack_damage(AttackType.PHYSICAL, attacker, defender, random.Random(seed))
        for seed in range(trials)
    )
    assert fast_total < full_total


def test_fast_attack_damage_range_matches_config():
    # Защищающийся с ТЕМИ ЖЕ статами - _compress_ratio(own, own) == 1.0,
    # сжатие не действует, диапазон урона равен исходному конфигу.
    attacker = make_stats(strength=100)
    defender = make_stats(strength=100)
    for seed in range(200):
        damage = raw_fast_attack_damage(AttackType.PHYSICAL, attacker, defender, random.Random(seed))
        assert 50.0 <= damage <= 80.0
