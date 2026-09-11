from typing import List, Optional

from aiogram.types import (
    InputRichBlockDetails,
    InputRichBlockList,
    InputRichBlockParagraph,
    InputRichMessage,
    RichTextBold,
)

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
    _flatten_to_plain_text,
)
from src.bot.services.dialog import DialogService

RANK_A = "F"
RANK_B = "D"


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


def _all_paragraph_lines(message: InputRichMessage) -> List[str]:
    """Разворачивает КАЖДЫЙ параграф сообщения (включая вложенные внутри
    Details -> List -> ListItem раунды) в plain text - тесты ниже проверяют
    смысл (что сказано), а не JSON-структуру rich-text (как именно жирность
    сериализуется) - для этого есть отдельные test_*_is_bold ниже."""

    assert message.blocks is not None
    lines: List[str] = []
    for block in message.blocks:
        if isinstance(block, InputRichBlockParagraph):
            lines.append(_flatten_to_plain_text(block.text))
        elif isinstance(block, InputRichBlockDetails):
            for inner in block.blocks or []:
                if isinstance(inner, InputRichBlockList):
                    for item in inner.items:
                        for inner_block in item.blocks:
                            if isinstance(inner_block, InputRichBlockParagraph):
                                lines.append(_flatten_to_plain_text(inner_block.text))
    return lines


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

    message = make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)

    assert isinstance(message, InputRichMessage)
    assert message.blocks
    dumped = message.model_dump_json(exclude_none=True)
    assert '"type":"heading"' in dumped
    assert '"type":"details"' in dumped
    assert '"type":"bold"' in dumped  # имена жирные - см. чат


def test_names_and_ranks_come_before_the_round_by_round_process():
    # Порядок (см. чат): имена+ранги -> ход боя -> итоги, а не наоборот.
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    lines = _all_paragraph_lines(
        make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)
    )

    assert lines[0] == "Гуль F ранга Канеки"
    assert lines[1] == "VS"
    assert lines[2] == "Гуль D ранга Крепкий боец"
    # Раунды (внутри Details) идут следом, итоги ("Победитель") - только
    # ПОСЛЕ них.
    round_index = next(i for i, line in enumerate(lines) if line.startswith("──── Раунд"))
    winner_index = next(i for i, line in enumerate(lines) if line.startswith("🏆 Победитель"))
    assert round_index < winner_index


def test_kagune_hit_uses_neutral_diamond_icon_not_squid():
    # См. чат - 🦑 заменён на ♦️, чтобы не объяснять игроку лор.
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    lines = _all_paragraph_lines(
        make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)
    )
    joined = "\n".join(lines)

    assert "♦️" in joined
    assert "🦑" not in joined


def test_fighter_names_are_rendered_bold():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    message = make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)

    assert isinstance(message.blocks, list)
    rank_paragraph = message.blocks[1]
    assert isinstance(rank_paragraph, InputRichBlockParagraph)
    assert isinstance(rank_paragraph.text, list)
    bold_segments = [seg for seg in rank_paragraph.text if isinstance(seg, RichTextBold)]
    assert bold_segments == [RichTextBold(text="Канеки")]


def test_rich_message_action_section_has_no_hp_numbers():
    # "Что произошло" (действие) и "итог раунда" (HP) - две РАЗНЫЕ секции,
    # см. чат: смешивание их в одну строку было главным источником путаницы
    # ("он лечится или умирает?" было неотвечаемо на глаз).
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    lines = _all_paragraph_lines(
        make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)
    )
    joined = "\n".join(lines)

    assert "Канеки наносит удар — 30 урона" in joined  # физическая атака A
    assert "Крепкий боец наносит удар — 20 урона" in joined  # атака кагуне B
    assert "Канеки промахивается" in joined  # промах A в раунде 2
    assert "Крепкий боец регенерирует — +15 HP" in joined  # регенерация B
    assert "Крепкий боец успевает ударить ещё раз — 10 урона" in joined  # бонус от speed


def test_landed_hit_that_rounds_to_zero_damage_says_did_not_break_through():
    # Регрессия (см. чат, реальный бой на статах свежего гуля - strength=1,
    # health=5-6): удар долетел (уклонение не сработало), но блок срезал
    # его почти целиком - "наносит удар - 0 урона" читается как баг
    # ("попал, но ничего не произошло?"), хотя механически честно. Слова
    # меняем, число (HP) - нет, поэтому этот тест ничего не проверяет на
    # уровне HP-цепочки - для неё отдельный тест ниже.
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    tiny_hit = RoundResult(
        round_number=1,
        actions_a=[AttackAction(hit=_hit(True, 0.3, AttackType.PHYSICAL))],
        actions_b=[FastAttackAction(hit=_hit(True, 0.4, AttackType.KAGUNE))],
        damage_to_a=0.4,
        damage_to_b=0.3,
    )
    result = BattleResult(
        rounds=[tiny_hit],
        winner=None,
        ended_naturally=False,
        final_hp_a=fighter_a.stats.health - 0.4,
        final_hp_b=fighter_b.stats.health - 0.3,
        stats_a=fighter_a.stats,
        stats_b=fighter_b.stats,
    )

    lines = _all_paragraph_lines(
        make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)
    )
    joined = "\n".join(lines)

    assert "Канеки не пробивает защиту" in joined
    assert "Крепкий боец не пробивает защиту" in joined
    assert "0 урона" not in joined
    assert "(не пробил)" in joined  # в итоговой HP-цепочке тоже, не только в "что произошло"
    assert "(0 урон)" not in joined


def test_regen_that_rounds_to_zero_heal_says_almost_no_effect():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    tiny_heal = RoundResult(
        round_number=1,
        actions_a=[RegenAction(healed=0.2, was_guaranteed=True)],
        actions_b=[AttackAction(hit=_hit(False))],
        damage_to_a=0.0,
        damage_to_b=0.0,
    )
    result = BattleResult(
        rounds=[tiny_heal],
        winner=None,
        ended_naturally=False,
        final_hp_a=fighter_a.stats.health,
        final_hp_b=fighter_b.stats.health,
        stats_a=fighter_a.stats,
        stats_b=fighter_b.stats,
    )

    lines = _all_paragraph_lines(
        make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)
    )
    joined = "\n".join(lines)

    assert "Канеки регенерирует, но почти не восстанавливает HP" in joined
    assert "+0 HP" not in joined


def test_rich_message_outcome_line_shows_full_hp_chain_with_causes():
    # Регрессия по мотивам чата: раньше строка вида "регенерирует (7 -> 19)"
    # молчала о том, что этот же боец в ЭТОМ ЖЕ раунде ещё и получает урон
    # (регенерация не защищает от урона, только замещает СВОЮ атаку) -
    # "лечится или умирает?" было неотвечаемо на глаз. Цепочка с причиной
    # каждого шага отвечает на это одним взглядом.
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    lines = _all_paragraph_lines(
        make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)
    )

    # После раунда 2: hp_b = 70 (после раунда 1) + 15 (регенерация), урона в
    # этом раунде B не получил (damage_to_b=0) - цепочка останавливается на
    # регенерации, шага "урон" в этом раунде для B нет.
    assert "❤️ Крепкий боец: 70 → 85 (+15 регенерация) HP" in lines


def test_rich_message_last_round_shows_display_hp_not_raw_zero_on_mutual_ko():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    lines = _all_paragraph_lines(
        make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)
    )

    # Честный расчёт (сложение damage_to_a/b по раундам) дал бы 0 HP у ОБОИХ
    # на раунде 3 - рендерер обязан подменить последний шаг цепочки на
    # result.final_hp_a/b (та же UX-подмена 2.6), иначе в логе будет
    # "0 против 0". Победитель (A) после подмены даже не помечается 💀, и
    # у подменённого шага НЕТ пометки "(-70 урон)" - она была бы враньём
    # (значение выросло с честного 0 до показанного 1, а не упало на 70).
    assert "❤️ Канеки: 70 → 1 HP" in lines
    assert "💀 Крепкий боец: 85 → 0 (-85 урон) HP — повержен" in lines
    # Регрессия (см. чат, реальный бой на статах 5-6 HP): подменённое
    # значение НЕ должно нести старую метку "урон"/"регенерация" - иначе
    # получается "0 -> 1 (-70 урон)" - HP выросло, подпись говорит обратное.
    assert not any("-70 урон" in line for line in lines)


def test_build_rich_message_includes_winner_line():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    lines = _all_paragraph_lines(
        make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)
    )
    joined = "\n".join(lines)

    assert "Победитель: Канеки" in joined
    assert "Крепкий боец: повержен." in joined


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

    lines = _all_paragraph_lines(
        make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)
    )

    assert any("Ничья" in line for line in lines)


def test_build_plain_text_is_condensed_without_per_round_breakdown():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Крепкий боец")
    result = make_battle_result(fighter_a, fighter_b)

    text = make_generator().build_plain_text(result, fighter_a, fighter_b, RANK_A, RANK_B)

    assert "Гуль F ранга Канеки" in text
    assert "VS" in text
    assert "Гуль D ранга Крепкий боец" in text
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

    message = make_generator().build_rich_message(result, fighter_a, fighter_b, RANK_A, RANK_B)
    for line in _all_paragraph_lines(message):
        assert _line_width(line) <= MAX_WIDTH_TEXT_RICH_MESSAGE, line

    plain_text = make_generator().build_plain_text(result, fighter_a, fighter_b, RANK_A, RANK_B)
    for line in plain_text.split("\n"):
        assert _line_width(line) <= MAX_WIDTH_TEXT_RICH_MESSAGE, line


def test_short_names_are_not_truncated():
    fighter_a, fighter_b = make_fighter(1, "Канеки"), make_fighter(2, "Тоука")
    result = make_battle_result(fighter_a, fighter_b)

    text = make_generator().build_plain_text(result, fighter_a, fighter_b, RANK_A, RANK_B)

    assert "…" not in text
    assert "Канеки" in text
    assert "Тоука" in text
