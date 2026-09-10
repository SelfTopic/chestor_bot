import random
from typing import Dict, Optional

import pytest

from src.bot.game_configs import BATTLE_CONFIG
from src.bot.services.battle_engine.core.battle import Battle
from src.bot.services.battle_engine.core.errors import InvalidBattleStatsError
from src.bot.services.battle_engine.core.fighter import Fighter, FighterSnapshot
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


def test_battle_never_exceeds_max_rounds():
    # Почти зеркальные бойцы - бой скорее дотянет до предела раундов.
    a = make_fighter(id=1, name="A")
    b = make_fighter(id=2, name="B")
    result = Battle(a, b, max_rounds=10).run(rng=random.Random(7))
    assert len(result.rounds) <= 10


def test_battle_ends_naturally_when_hp_hits_zero():
    strong = make_fighter(id=1, name="Сильный", strength=100_000, health=100_000)
    weak = make_fighter(id=2, name="Слабый", strength=1, health=1)
    result = Battle(strong, weak, max_rounds=100).run(rng=random.Random(3))
    assert result.ended_naturally
    assert result.winner == "a"
    assert len(result.rounds) < 100


def test_invalid_fighter_stats_raise_before_battle_is_even_created():
    with pytest.raises(InvalidBattleStatsError):
        make_fighter(dexterity=0)


# --- Обоюдный нокаут (2.6) - UX-подмена HP победителя ----------------------


def test_mutual_ko_winner_shown_with_symbolic_hp_not_zero():
    # Белый ящик - честно словить обоюдный нокаут сидом дорого, проще
    # смоделировать состояние прямо перед сборкой результата.
    a = make_fighter(id=1, name="A", health=100)
    b = make_fighter(id=2, name="B", health=100)
    battle = Battle(a, b, max_rounds=1)
    battle._hp_a_before_last = 80.0  # A имел больше HP до последнего обмена
    battle._hp_b_before_last = 60.0
    a.take_damage(1000)
    b.take_damage(1000)

    result = battle._build_result()

    assert a.is_defeated and b.is_defeated
    assert result.winner == "a"
    assert result.final_hp_a == BATTLE_CONFIG.mutual_ko_winner_hp
    assert result.final_hp_a != 0.0
    assert result.final_hp_b == 0.0


def test_mutual_ko_true_draw_does_not_bump_either_side():
    a = make_fighter(id=1, name="A", health=100)
    b = make_fighter(id=2, name="B", health=100)
    battle = Battle(a, b, max_rounds=1)
    battle._hp_a_before_last = 50.0
    battle._hp_b_before_last = 50.0
    a.take_damage(1000)
    b.take_damage(1000)

    result = battle._build_result()

    assert result.winner is None
    assert result.final_hp_a == 0.0
    assert result.final_hp_b == 0.0


def test_battle_is_deterministic_with_same_seed():
    a1, b1 = make_fighter(id=1, name="A"), make_fighter(id=2, name="B")
    a2, b2 = make_fighter(id=1, name="A"), make_fighter(id=2, name="B")

    result1 = Battle(a1, b1).run(rng=random.Random(123))
    result2 = Battle(a2, b2).run(rng=random.Random(123))

    assert result1.winner == result2.winner
    assert result1.final_hp_a == pytest.approx(result2.final_hp_a)
    assert result1.final_hp_b == pytest.approx(result2.final_hp_b)
    assert len(result1.rounds) == len(result2.rounds)


def test_play_round_step_by_step_matches_run_to_completion():
    # Пошаговый play_round() и разовый run() должны давать одинаковый
    # результат при одном и том же сиде - оба используют один и тот же rng.
    a_run, b_run = make_fighter(id=1, name="A"), make_fighter(id=2, name="B")
    run_result = Battle(a_run, b_run, max_rounds=20).run(rng=random.Random(5))

    a_step, b_step = make_fighter(id=1, name="A"), make_fighter(id=2, name="B")
    battle = Battle(a_step, b_step, max_rounds=20)
    rng = random.Random(5)
    while not battle.is_finished:
        battle.play_round(rng)
    step_result = battle.run(rng)  # уже закончен - просто соберёт BattleResult

    assert len(battle.rounds) == len(run_result.rounds)
    # Сырое состояние Fighter должно совпадать точь-в-точь между двумя
    # способами - это то, что реально просимулировано. BattleResult.final_hp
    # сверяем отдельно (ниже) - при обоюдном нокауте он может отличаться от
    # current_hp самого Fighter (см. mutual_ko_winner_hp, UX-подмена).
    assert a_step.current_hp == pytest.approx(a_run.current_hp)
    assert b_step.current_hp == pytest.approx(b_run.current_hp)
    assert step_result.winner == run_result.winner
    assert step_result.final_hp_a == pytest.approx(run_result.final_hp_a)
    assert step_result.final_hp_b == pytest.approx(run_result.final_hp_b)


def test_play_round_raises_after_battle_already_finished():
    strong = make_fighter(id=1, strength=100_000, health=100_000)
    weak = make_fighter(id=2, strength=1, health=1)
    battle = Battle(strong, weak, max_rounds=100)
    battle.run(rng=random.Random(1))
    assert battle.is_finished
    with pytest.raises(RuntimeError):
        battle.play_round(rng=random.Random(1))
