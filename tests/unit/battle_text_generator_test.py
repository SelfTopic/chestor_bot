from typing import Optional

from aiogram.types import InputRichBlockParagraph, InputRichMessage

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
from src.bot.services.battle_engine.text_generator import (
    MAX_WIDTH_TEXT_RICH_MESSAGE,
    BattleTextGenerator,
)
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
    # После раунда 2: hp_a=70, hp_b=70+15(регенерация)=85 - именно этот "+15"
    # раньше терялся в _apply_round_hp_change (см. scripts/battle_text_demo.py,
    # нашли через живой прогон, регенерация не учитывалась в бегущем HP).

    round_3 = RoundResult(
        round_number=3,
        actions_a=[AttackAction(hit=_hit(True, 85.0, AttackType.PHYSICAL))],  # добивает hp_b=85
        actions_b=[DefenseAction()],  # зарезервированный тип - не должен падать
        damage_to_a=70.0,  # добивает hp_a=70
        damage_to_b=85.0,
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


def test_rich_message_action_section_has_no_hp_numbers():
    # "Что произошло" (действие) и "итог раунда" (HP) - две РАЗНЫЕ секции,
    # см. чат: смешивание их в одну строку было главным источником путаницы
    # ("он лечится или умирает?" было неотвечаемо на глаз).
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    dumped = make_generator().build_rich_message(result, fighter_a, fighter_b).model_dump_json(
        exclude_none=True
    )

    assert "👊 Канеки наносит удар — 30 урона" in dumped  # физическая атака A
    assert "🦑 Крепкий боец наносит удар — 20 урона" in dumped  # атака кагуне B
    assert "💨 Канеки промахивается" in dumped  # промах A в раунде 2
    assert "💊 Крепкий боец регенерирует — +15 HP" in dumped  # регенерация B
    assert "⚡👊 Крепкий боец успевает ударить ещё раз — 10 урона" in dumped  # бонус от speed


def test_rich_message_outcome_line_shows_full_hp_chain_with_causes():
    # Регрессия по мотивам чата: раньше строка вида "регенерирует (7 -> 19)"
    # молчала о том, что этот же боец в ЭТОМ ЖЕ раунде ещё и получает урон
    # (регенерация не защищает от урона, только замещает СВОЮ атаку) -
    # "лечится или умирает?" было неотвечаемо на глаз. Цепочка с причиной
    # каждого шага отвечает на это одним взглядом.
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    dumped = make_generator().build_rich_message(result, fighter_a, fighter_b).model_dump_json(
        exclude_none=True
    )

    # После раунда 2: hp_b = 70 (после раунда 1) + 15 (регенерация), урона в
    # этом раунде B не получил (damage_to_b=0) - цепочка останавливается на
    # регенерации, шага "урон" в этом раунде для B нет.
    assert "❤️ Крепкий боец: 70 → 85 (+15 регенерация) HP" in dumped


def test_rich_message_last_round_shows_display_hp_not_raw_zero_on_mutual_ko():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    dumped = make_generator().build_rich_message(result, fighter_a, fighter_b).model_dump_json(
        exclude_none=True
    )

    # Честный расчёт (сложение damage_to_a/b по раундам) дал бы 0 HP у ОБОИХ
    # на раунде 3 - рендерер обязан подменить последний шаг цепочки на
    # result.final_hp_a/b (та же UX-подмена 2.6), иначе в логе будет
    # "0 против 0". Победитель (A) после подмены даже не помечается 💀.
    assert "❤️ Канеки: 70 → 1 (-70 урон) HP" in dumped
    assert "💀 Крепкий боец: 85 → 0 (-85 урон) HP — повержен" in dumped


def test_build_rich_message_includes_winner_line():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    dumped = make_generator().build_rich_message(result, fighter_a, fighter_b).model_dump_json(
        exclude_none=True
    )

    assert "Победитель: Канеки" in dumped
    assert "Крепкий боец: повержен." in dumped


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


# --- MAX_WIDTH_TEXT_RICH_MESSAGE - ни одна строка не переносится ------------


def _line_width(line: str) -> int:
    return len(line.replace(" ", ""))


def test_no_line_exceeds_max_width_even_with_a_pathologically_long_name():
    # Реальный триггер этой правки (см. чат): длинное имя, склеенное в одну
    # строку с чужим именем/иконками, переносилось на вторую строку в
    # Telegram и портило вёрстку. Оба бойца намеренно с длинными именами -
    # ни одна строка не должна превысить бюджет ни в rich, ни в plain.
    long_name_a = "Очень-очень-очень-длинное-имя-первого-гуля-которое-никогда-не-влезет"
    long_name_b = "Не менее длинное имя второго гуля с кучей слов подряд"
    fighter_a = make_fighter(1, long_name_a)
    fighter_b = make_fighter(2, long_name_b)
    result = make_battle_result(fighter_a, fighter_b)

    message = make_generator().build_rich_message(result, fighter_a, fighter_b)
    assert message.blocks is not None
    rich_lines = [
        block.text
        for block in message.blocks
        if isinstance(block, InputRichBlockParagraph) and isinstance(block.text, str)
    ]
    for line in rich_lines:
        assert _line_width(line) <= MAX_WIDTH_TEXT_RICH_MESSAGE, line

    generator = make_generator()
    round_lines = generator._round_lines(result, fighter_a, fighter_b)
    for line in round_lines:
        assert _line_width(line) <= MAX_WIDTH_TEXT_RICH_MESSAGE, line

    plain_text = make_generator().build_plain_text(result, fighter_a, fighter_b)
    for line in plain_text.split("\n"):
        assert _line_width(line) <= MAX_WIDTH_TEXT_RICH_MESSAGE, line


def test_short_names_are_not_truncated():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Тоука")
    result = make_battle_result(fighter_a, fighter_b)

    text = make_generator().build_plain_text(result, fighter_a, fighter_b)

    assert "…" not in text
    assert "Канеки" in text
    assert "Тоука" in text
