from typing import Optional

from aiogram.types import InputRichMessage

from src.bot.services.battle_engine.core import (
    AttackAction,
    AttackType,
    BattleResult,
    DefenseAction,
    FastAttackAction,
    Fighter,
    FighterSnapshot,
    HitResult,
    RegenAction,
    RoundResult,
)
from src.bot.services.battle_engine.text_generator import BattleTextGenerator
from src.bot.services.dialog import DialogService


def make_fighter(id: int = 1, name: str = "Тест", health: int = 100) -> Fighter:
    return Fighter(
        FighterSnapshot(
            id=id,
            name=name,
            strength=100,
            dexterity=100,
            regeneration=100,
            speed=100,
            health=health,
            hunger=100,
            is_kakuja=False,
            kagune_strength={},
        )
    )


def _hit(landed: bool, damage: float = 0.0, attack_type: Optional[AttackType] = None) -> HitResult:
    return HitResult(landed=landed, attack_type=attack_type, damage=damage)


def make_generator() -> BattleTextGenerator:
    return BattleTextGenerator(dialog_service=DialogService())


def make_battle_result(fighter_a: Fighter, fighter_b: Fighter) -> BattleResult:
    """Синтетический бой (без реального Battle.run()) - раунды собраны
    вручную, чтобы детерминированно проверить рендер каждого типа действия
    и обоюдный нокаут на последнем раунде. Стартовые HP обоих - 100."""

    round_1 = RoundResult(
        round_number=1,
        actions_a=[AttackAction(hit=_hit(True, 30.0, AttackType.PHYSICAL))],
        actions_b=[AttackAction(hit=_hit(True, 20.0, AttackType.KAGUNE))],
        damage_to_a=20.0,  # A получает урон ОТ B
        damage_to_b=30.0,  # B получает урон ОТ A
    )
    # После раунда 1: hp_a=80, hp_b=70

    round_2 = RoundResult(
        round_number=2,
        actions_a=[AttackAction(hit=_hit(False))],
        actions_b=[
            RegenAction(healed=15.0, was_guaranteed=True),
            FastAttackAction(hit=_hit(True, 10.0, AttackType.PHYSICAL)),
        ],
        damage_to_a=10.0,
        damage_to_b=0.0,
    )
    # После раунда 2: hp_a=70, hp_b=70

    round_3 = RoundResult(
        round_number=3,
        actions_a=[AttackAction(hit=_hit(True, 70.0, AttackType.PHYSICAL))],
        actions_b=[DefenseAction()],  # зарезервированный тип - не должен падать
        damage_to_a=70.0,
        damage_to_b=70.0,
    )
    # После раунда 3: honest hp_a=0, hp_b=0 - обоюдный нокаут, A выиграл тай-брейк

    return BattleResult(
        rounds=[round_1, round_2, round_3],
        winner="a",
        ended_naturally=True,
        final_hp_a=1.0,  # UX-подмена победителя (2.6) - честный 0 не показываем
        final_hp_b=0.0,
        stats_a=fighter_a.stats,
        stats_b=fighter_b.stats,
    )


def test_build_rich_message_returns_valid_input_rich_message():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    message = make_generator().build_rich_message(result, fighter_a, fighter_b)

    assert isinstance(message, InputRichMessage)
    assert message.blocks
    dumped = message.model_dump_json(exclude_none=True)
    assert '"type":"heading"' in dumped
    assert '"type":"details"' in dumped


def test_rich_message_renders_every_action_type_with_its_own_icon():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    dumped = make_generator().build_rich_message(result, fighter_a, fighter_b).model_dump_json(
        exclude_none=True
    )

    assert "👊 30" in dumped  # физическая атака A
    assert "🦑 20" in dumped  # атака кагуне B
    assert "💨 промах" in dumped  # промах A в раунде 2
    assert "💊 +15" in dumped  # регенерация B
    assert "⚡👊 10" in dumped  # бонусный удар от speed - B
    assert "—" in dumped  # DefenseAction (зарезервированный тип) не падает


def test_rich_message_last_round_shows_display_hp_not_raw_zero_on_mutual_ko():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    dumped = make_generator().build_rich_message(result, fighter_a, fighter_b).model_dump_json(
        exclude_none=True
    )

    # Честный расчёт (сложение damage_to_a/b по раундам) дал бы 0 HP у ОБОИХ
    # на раунде 3 - рендерер обязан подменить его на result.final_hp_a/b
    # (та же UX-подмена 2.6), иначе в логе будет "0 против 0".
    assert "Канеки 👊 70 (1 HP)" in dumped
    assert "Крепкий боец — (0 HP)" in dumped


def test_build_rich_message_includes_winner_line():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    dumped = make_generator().build_rich_message(result, fighter_a, fighter_b).model_dump_json(
        exclude_none=True
    )

    assert "Победитель: Канеки" in dumped
    assert "Крепкий боец повержен" in dumped


def test_build_rich_message_true_draw_says_nichya():
    fighter_a, fighter_b = make_fighter(1, "A"), make_fighter(2, "B")
    base = make_battle_result(fighter_a, fighter_b)
    result = BattleResult(
        rounds=base.rounds,
        winner=None,
        ended_naturally=False,
        final_hp_a=10.0,
        final_hp_b=10.0,
        stats_a=fighter_a.stats,
        stats_b=fighter_b.stats,
    )

    dumped = make_generator().build_rich_message(result, fighter_a, fighter_b).model_dump_json(
        exclude_none=True
    )

    assert "Ничья" in dumped


def test_build_plain_text_is_condensed_without_per_round_breakdown():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    text = make_generator().build_plain_text(result, fighter_a, fighter_b)

    assert "Канеки" in text
    assert "Крепкий боец" in text
    assert "Победитель: Канеки" in text
    assert "Раундов: 3" in text  # только счётчик...
    assert "Раунд 1" not in text  # ...без самого списка раундов, см. docstring
