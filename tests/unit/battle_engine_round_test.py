import random
from typing import Dict, Optional

from src.bot.services.battle_engine.core.actions import RoundActionType
from src.bot.services.battle_engine.core.battle import Battle
from src.bot.services.battle_engine.core.fighter import Fighter, FighterSnapshot
from src.bot.services.battle_engine.core.formulas import AttackType
from src.bot.services.battle_engine.core.hit import resolve_hit
from src.bot.types import KaguneType


def make_fighter(
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
) -> Fighter:
    return Fighter(
        FighterSnapshot(
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
    )


# --- resolve_hit - streak физических ударов --------------------------------


def test_resolve_hit_first_hit_is_always_physical_and_advances_streak():
    # Ловкость защищающегося намного ниже - уклонение у пола (~5%), почти
    # все прогоны landed=True, удобно набрать много попаданий на тест.
    attacker = make_fighter(id=1, dexterity=1000)
    defender = make_fighter(id=2, dexterity=1)

    landed_count = 0
    for seed in range(100):
        hit = resolve_hit(attacker, defender, rng=random.Random(seed))
        if hit.landed:
            landed_count += 1
            assert hit.attack_type is AttackType.PHYSICAL
            assert hit.physical_chance_used == 100.0
            assert attacker.physical_streak == 1
            attacker.physical_streak = 0  # сброс для следующей итерации теста
    assert landed_count > 0


def test_resolve_hit_kagune_landing_does_not_advance_streak():
    attacker = make_fighter(id=1, dexterity=1000)
    defender = make_fighter(id=2, dexterity=1)
    attacker.physical_streak = 5

    found_kagune_hit = False
    for seed in range(200):
        attacker.physical_streak = 5
        hit = resolve_hit(attacker, defender, rng=random.Random(seed))
        if hit.landed and hit.attack_type is AttackType.KAGUNE:
            found_kagune_hit = True
            assert attacker.physical_streak == 5  # не сдвинулся
        elif hit.landed:
            assert attacker.physical_streak == 6  # физический удар - сдвинулся на 1
    assert found_kagune_hit  # при streak=5 (50% физика/50% кагуне) должен найтись хоть один


# --- decide_action - Attack vs Regen ----------------------------------------


def test_decide_action_returns_attack_when_not_critical():
    fighter = make_fighter(health=100)
    opponent = make_fighter()
    assert fighter.decide_action(opponent, random.Random(0)) is RoundActionType.ATTACK


def test_decide_action_first_critical_dip_is_guaranteed_regen():
    fighter = make_fighter(health=100)
    opponent = make_fighter()
    fighter.take_damage(95)  # 5 HP - ниже 10% порога

    action = fighter.decide_action(opponent, random.Random(0))
    assert action is RoundActionType.REGEN
    assert fighter.regen_guaranteed_used is True
    assert fighter.regen_roll_used is False


def test_decide_action_second_regen_check_happens_only_once():
    fighter = make_fighter(health=100, regeneration=100)
    opponent = make_fighter(regeneration=100)  # равная регенерация -> 0% шанс второго прока
    fighter.take_damage(95)

    first = fighter.decide_action(opponent, random.Random(0))
    assert first is RoundActionType.REGEN  # гарантированный

    fighter.take_damage(0)  # всё ещё критический (урона не было)
    second = fighter.decide_action(opponent, random.Random(0))
    assert second is RoundActionType.ATTACK  # равная регенерация -> шанс 0%, но попытка потрачена
    assert fighter.regen_roll_used is True

    third = fighter.decide_action(opponent, random.Random(0))
    assert third is RoundActionType.ATTACK  # оба прока исчерпаны навсегда


def test_decide_action_not_critical_after_healing_back_above_threshold():
    fighter = make_fighter(health=100)
    opponent = make_fighter()
    fighter.take_damage(95)
    fighter.apply_heal(random.Random(0))  # первый прок восстанавливает HP
    assert not fighter.is_critical()
    assert fighter.decide_action(opponent, random.Random(0)) is RoundActionType.ATTACK


# --- Регенерация замещает атаку, НО не бонусный удар от speed --------------


def test_regen_round_deals_no_damage_from_attack_action():
    fighter = make_fighter(health=100, speed=100)
    opponent = make_fighter(speed=100, strength=1)
    fighter.take_damage(95)

    battle = Battle(fighter, opponent, max_rounds=1)
    result = battle.play_round(rng=random.Random(0))

    kinds = [type(a).__name__ for a in result.actions_a]
    assert "AttackAction" not in kinds
    assert "RegenAction" in kinds


def test_fast_fighter_can_regen_and_still_land_a_bonus_hit_same_round():
    # Огромная скорость гарантирует лишние удары почти всегда - критичный
    # боец должен получить и RegenAction, и хотя бы FastAttackAction.
    found_combo = False
    for seed in range(50):
        f = make_fighter(health=100, speed=100_000, regeneration=100_000, strength=50)
        o = make_fighter(speed=100, health=1000)
        f.take_damage(95)
        battle = Battle(f, o, max_rounds=1)
        result = battle.play_round(rng=random.Random(seed))
        kinds = [type(a).__name__ for a in result.actions_a]
        if "RegenAction" in kinds and "FastAttackAction" in kinds:
            found_combo = True
            break
    assert found_combo
