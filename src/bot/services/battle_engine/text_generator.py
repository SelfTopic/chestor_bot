"""Рендерер `BattleResult` в то, что реально увидит игрок - первый
Telegram-фасад боевого движка (BATTLE_DESIGN.md прямо предвидел это
разделение "лог событий боя" / "как его показать"). Живёт на уровне
`battle_engine/`, а не `core/` - тянет aiogram-типы и `DialogService`,
а `core/` обязан оставаться чистым доменом без БД/Telegram-зависимостей.

Только ИТОГОВАЯ сводка по всему бою (см. чат) - не пораундовая анимация
через `Battle.play_round()` + `edit_text()`. Та фича сложнее (таймеры,
rate-limit Telegram на редактирование сообщений, обрыв на середине) и
пока не нужна - `BattleTextGenerator` рендерит уже завершённый бой целиком
одним сообщением, раунды доступны игроку под сворачиваемым блоком.

Класс, а не свободная функция `build_X_rich_message`, как в
`race_profile_router.py` - осознанное отступление от стиля проекта,
подтверждено автором (в отличие от `build_ghoul_profile_rich_message`,
здесь два публичных метода делят приватные хелперы форматирования одного
раунда/действия, и в будущем добавится третий - пораундовый рендер для
анимации, - которому те же хелперы тоже понадобятся).

Формат раунда - "что произошло" / "итог раунда" РАЗДЕЛЬНО (см. чат,
результат нескольких итераций вручную нарисованного автором мокапа):
- Первая версия клеила два имени и HP в одну строку ("Раунд N: A ... —
  B ...") - переносилась на экране (см. MAX_WIDTH_TEXT_RICH_MESSAGE).
- Вторая (по одному имени на строку) читалась только "обученным" - число
  без подписи ("(43 HP)") не говорит, ЧЬЁ это HP и относится ли оно к
  этому раунду целиком или к одному конкретному удару.
- Третья проблема, вскрытая автором вручную: строка вида "gojoat666
  регенерирует (7 -> 19)" молчит о том, что этот же боец в ЭТОМ ЖЕ раунде
  ещё и получает урон (регенерация не защищает от урона - она замещает
  только СОБСТВЕННУЮ атаку, см. REGENERATION.md) - "он лечится или
  умирает?" было неотвечаемо на глаз.

Решение: секция "что произошло" ВООБЩЕ не содержит чисел HP (только
действие и его прямой эффект - урон/лечение) - там физически негде
перепутать, чьё и какое HP. Секция "итог раунда" считается ОДИН раз,
после того как весь раунд (оба бойца, вся регенерация, весь урон)
полностью разрешён, и показывает ПОЛНУЮ цепочку "было -> стало (причина)"
для каждого бойца отдельно - "7 -> 19 (+12 регенерация) -> 0 (-24 урон)"
отвечает на "лечится или умирает" одним взглядом, без потребности знать
про одновременность действий в раунде.

Порядок блоков сообщения (см. чат, по мотивам мокапа автора): имена+ранги
-> сворачиваемый ход боя -> итоги. Раньше итоги были ПЕРВЫМИ - но тогда
игрок видит "кто выиграл" раньше, чем сам процесс, а по мокапу автора
итоги - это развязка, идущая ПОСЛЕ хода поединка. Имя бойца - жирным
(`RichTextBold`) везде, где оно встречается - и в "Гуль X ранга **имя**",
и в "что произошло", и в "итоге раунда", и в финальных строках победителя/
HP. Кагуне-удар - нейтральный ♦️ вместо 🦑 (см. чат: автору не хочется
объяснять игроку, почему кальмар)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from aiogram.types import (
    InputRichBlockDetails,
    InputRichBlockDivider,
    InputRichBlockList,
    InputRichBlockListItem,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockUnion,
    InputRichMessage,
    RichTextBold,
    RichTextUnion,
)

from ..dialog import DialogService
from .core import (
    AttackAction,
    AttackType,
    BattleResult,
    DefenseAction,
    FastAttackAction,
    Fighter,
    HitResult,
    IdleAction,
    RegenAction,
    RoundAction,
)

_HIT_ICON = {AttackType.PHYSICAL: "👊", AttackType.KAGUNE: "♦️"}

# Имя бойца - переменной длины (полное имя из Telegram), и раньше клеилось
# в одну строку вместе с именем ВТОРОГО бойца ("Раунд N: A ... — B ...") -
# на узком экране это неизбежно переносится на вторую строку и ломает
# верстку. MAX_WIDTH_TEXT_RICH_MESSAGE - порог длины ОДНОЙ строки (без
# пробелов - см. чат: взята длина строки "валютой.Однако на переводы
# налагаются следующие ограничения" из реального RichMessage в канале
# автора, которая перенеслась на вторую строку). Каждая строка ниже
# содержит РОВНО ОДНО имя и обрезается под этот бюджет (с "…"), а не два
# имени сразу - главная защита от переноса.
MAX_WIDTH_TEXT_RICH_MESSAGE = 54

# Строка с именем - список сегментов (не голая str), потому что имя внутри
# всегда обёрнуто в RichTextBold (см. чат: "все имена бойцов должны быть
# жирно выделенные") - `InputRichBlockParagraph.text` принимает именно
# такой список (`RichTextUnion` включает `list[RichTextUnion]`), смешивая
# обычные строки и форматированные куски в одном поле. Тип - алиас на сам
# `RichTextUnion` (не `List[Union[str, RichTextBold]]`) - `list` в pyright
# инвариантен, и более узкий список не проходит структурную проверку под
# рекурсивный `RichTextUnion`, даже когда реально в него укладывается.
RichLine = RichTextUnion


def _truncate_to_width(text: str, max_width: int) -> str:
    """Обрезает text так, чтобы len(результат.replace(' ', '')) <= max_width,
    считая длину БЕЗ ПРОБЕЛОВ (см. MAX_WIDTH_TEXT_RICH_MESSAGE) - пробелы
    сами по себе занимают меньше места на экране, чем буквы, поэтому их не
    считаем при принятии решения "влезаем/не влезаем"."""

    if len(text.replace(" ", "")) <= max_width:
        return text

    # Сам символ "…" тоже занимает единицу бюджета - если резервировать
    # место только ПОД ИМЯ (max_width), результат "имя…" окажется на 1
    # символ длиннее max_width (одна из версий этой функции так и упала).
    budget = max(0, max_width - 1)
    non_space_count = 0
    for i, char in enumerate(text):
        if char != " ":
            non_space_count += 1
        if non_space_count > budget:
            return text[:i].rstrip() + "…"
    return text.rstrip() + "…"


def _fit_line(
    name: str, prefix: str = "", suffix: str = "", max_width: int = MAX_WIDTH_TEXT_RICH_MESSAGE
) -> RichLine:
    """Собирает `[prefix, ЖИРНОЕ_имя, suffix]`, обрезая ИМЕННО name (а не
    конец строки вслепую) так, чтобы вся строка целиком (без учёта того,
    что имя ещё и жирное - жирность не меняет число символов) не превышала
    max_width. prefix/suffix (иконки, HP, счётчики) всегда остаются
    целыми - это они несут игровую информацию, обрезать есть смысл только
    переменную по длине часть (имя)."""

    fixed_width = len((prefix + suffix).replace(" ", ""))
    name_budget = max(1, max_width - fixed_width)
    fitted_name = _truncate_to_width(name, name_budget)
    return [prefix, RichTextBold(text=fitted_name), suffix]


def _flatten_to_plain_text(value: object) -> str:
    """Обратное превращение RichLine (или голой строки) в plain text - для
    `build_plain_text`, где жирность выразить нечем (это шаблон в
    dialogs.json, обычная строка), но обрезка имени должна остаться той же
    самой, поэтому и rich, и plain строятся из ОДНИХ И ТЕХ ЖЕ `_fit_line`,
    просто plain-версия дополнительно "разворачивает" результат в str."""

    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_flatten_to_plain_text(item) for item in value)
    if isinstance(value, RichTextBold):
        return _flatten_to_plain_text(value.text)
    raise TypeError(f"Не умею превращать {type(value)!r} в plain text")


# --- "Что произошло" - действие само по себе, БЕЗ единого числа HP ---------


def _hit_verb_and_icon(hit: HitResult, is_fast: bool) -> Tuple[str, str]:
    if not hit.landed or hit.attack_type is None:
        icon = "⚡💨" if is_fast else "💨"
        verb = "не успевает ударить ещё раз" if is_fast else "промахивается"
        return icon, verb

    base_icon = _HIT_ICON[hit.attack_type]
    icon = f"⚡{base_icon}" if is_fast else base_icon
    verb = "успевает ударить ещё раз" if is_fast else "наносит удар"
    return icon, f"{verb} — {round(hit.damage)} урона"


def _action_icon_and_text(action: RoundAction) -> "Optional[Tuple[str, str]]":
    """None - для DEFENSE/IDLE (зарезервированы в actions.py, decide_action
    их пока никогда не возвращает, но рендерер не должен упасть, если это
    изменится без обновления этого файла) - рассказывать о них нечего,
    секция "что произошло" их просто пропускает."""

    if isinstance(action, RegenAction):
        return "💊", f"регенерирует — +{round(action.healed)} HP"
    if isinstance(action, AttackAction):
        return _hit_verb_and_icon(action.hit, is_fast=False)
    if isinstance(action, FastAttackAction):
        return _hit_verb_and_icon(action.hit, is_fast=True)
    if isinstance(action, (DefenseAction, IdleAction)):
        return None
    raise NotImplementedError(f"Неизвестный тип действия для рендера: {type(action)!r}")


def _action_lines(fighter: Fighter, actions: List[RoundAction]) -> List[RichLine]:
    lines: List[RichLine] = []
    for action in actions:
        icon_and_text = _action_icon_and_text(action)
        if icon_and_text is None:
            continue
        icon, text = icon_and_text
        lines.append(_fit_line(fighter.name, prefix=f"{icon} ", suffix=f" {text}"))
    return lines


# --- "Итог раунда" - цепочка HP-шагов на бойца, посчитанная ОДИН раз -------


@dataclass(frozen=True)
class _HpStep:
    value: float
    delta: Optional[float] = None  # None - стартовое значение раунда
    cause: Optional[str] = None


def _build_hp_trajectory(hp_before: float, healed: float, damage: float) -> List[_HpStep]:
    """Порядок шагов повторяет ПОРЯДОК движка (Battle._play_one_round):
    сначала регенерация (Fighter.apply_heal внутри _resolve_participant),
    потом урон (take_damage - последней строкой, уже после того как ОБА
    бойца полностью резолвились). Регенерация НЕ защищает от урона в этом
    же раунде - именно поэтому оба шага в одной цепочке, а не альтернативы
    друг другу."""

    steps = [_HpStep(value=hp_before)]
    current = hp_before
    if healed > 0:
        current = current + healed
        steps.append(_HpStep(value=current, delta=healed, cause="регенерация"))
    if damage > 0:
        current = max(0.0, current - damage)
        steps.append(_HpStep(value=current, delta=-damage, cause="урон"))
    return steps


def _format_hp_chain(steps: List[_HpStep]) -> str:
    if len(steps) == 1:
        return f"{round(steps[0].value)} HP (без изменений)"

    parts = [str(round(steps[0].value))]
    for step in steps[1:]:
        if step.cause is None:
            # UX-подмена mutual_ko_winner_hp (2.6, см. _apply_mutual_ko_display) -
            # причина потеряла смысл (значение уже не честное), поэтому без
            # причины/дельты вообще, а не с устаревшей меткой "урон"/
            # "регенерация" - иначе получится "0 -> 1 (-1 урон)", то есть
            # HP выросло, а подпись утверждает обратное.
            parts.append(str(round(step.value)))
            continue
        delta = step.delta or 0.0
        sign = "+" if delta >= 0 else ""
        parts.append(f"{round(step.value)} ({sign}{round(delta)} {step.cause})")
    return " → ".join(parts) + " HP"


def _fighter_outcome_line(fighter: Fighter, steps: List[_HpStep]) -> RichLine:
    is_defeated = steps[-1].value <= 0
    prefix = "💀 " if is_defeated else "❤️ "
    suffix = f": {_format_hp_chain(steps)}" + (" — повержен" if is_defeated else "")
    return _fit_line(fighter.name, prefix=prefix, suffix=suffix)


def _apply_mutual_ko_display(steps: List[_HpStep], final_hp: float) -> List[_HpStep]:
    """Подменяет ЗНАЧЕНИЕ последнего шага, но НЕ его delta/cause - те
    посчитаны для честного (непоказанного) числа и после подмены больше
    не соответствуют действительности. Раньше подмена сохраняла старые
    delta/cause, из-за чего строка могла выглядеть как "0 -> 1 (-1 урон)" -
    HP выросло, а подпись утверждает обратное (см. чат, реальный бой на
    малых статах, где это проявилось)."""

    if not steps or steps[-1].value == final_hp:
        return steps
    return steps[:-1] + [_HpStep(value=final_hp)]


class BattleTextGenerator:
    """Требует `Fighter` для ОБЕИХ сторон отдельно от `BattleResult` -
    `BattleResult.stats_a/stats_b` это голые `EffectiveStats` без имени/id
    (см. чат), имя живёт только на `Fighter.name`/`FighterSnapshot.name`.

    `rank_a`/`rank_b` - буква ранга опасности ("F", "D", ...), считается
    снаружи (`GhoulService.get_danger_rank`) - `battle_engine` намеренно
    не знает про ранги/БД, это чужая ответственность (см. модульный
    докстринг про core/ без БД - тот же принцип и для этого слоя)."""

    def __init__(self, dialog_service: DialogService) -> None:
        self._dialog_service = dialog_service

    def build_rich_message(
        self,
        result: BattleResult,
        fighter_a: Fighter,
        fighter_b: Fighter,
        rank_a: str,
        rank_b: str,
    ) -> InputRichMessage:
        rank_line_a = _fit_line(fighter_a.name, prefix=f"Гуль {rank_a} ранга ")
        rank_line_b = _fit_line(fighter_b.name, prefix=f"Гуль {rank_b} ранга ")
        winner_line, loser_line = self._winner_lines(result, fighter_a, fighter_b)
        hp_line_a, hp_line_b = self._hp_lines(result, fighter_a, fighter_b)

        # Порядок (см. чат): имена+ранги -> ход боя -> итоги. Итоги - это
        # развязка, они идут ПОСЛЕ процесса, а не до него.
        blocks: List[InputRichBlockUnion] = [
            InputRichBlockSectionHeading(text="⚔️ Бой", size=3),
            InputRichBlockParagraph(text=rank_line_a),
            InputRichBlockParagraph(text="VS"),
            InputRichBlockParagraph(text=rank_line_b),
        ]

        if result.rounds:
            blocks.append(
                InputRichBlockDetails(
                    summary=f"📜 Ход поединка ({len(result.rounds)} раунд(ов))",
                    blocks=[
                        InputRichBlockList(
                            items=[
                                InputRichBlockListItem(
                                    blocks=[InputRichBlockParagraph(text=line)]
                                )
                                for line in self._round_lines(result, fighter_a, fighter_b)
                            ]
                        )
                    ],
                )
            )

        blocks.append(InputRichBlockDivider())
        blocks.extend(
            [
                InputRichBlockParagraph(text=winner_line),
                InputRichBlockParagraph(text=loser_line),
                InputRichBlockParagraph(text=hp_line_a),
                InputRichBlockParagraph(text=hp_line_b),
            ]
        )

        return InputRichMessage(blocks=blocks)

    def build_plain_text(
        self,
        result: BattleResult,
        fighter_a: Fighter,
        fighter_b: Fighter,
        rank_a: str,
        rank_b: str,
    ) -> str:
        """Фолбэк на случай, если `answer_rich` недоступен (см.
        race_profile_router.py - тот же паттерн try/except TelegramAPIError).
        Намеренно БЕЗ раундов - в отличие от rich-версии, здесь их некуда
        свернуть, а бой может идти 20-30 раундов (и теперь каждый раунд -
        это несколько строк "что произошло" + "итог", не одна); полный лог
        только в rich-сообщении, тут - голая сводка. Жирность имён негде
        выразить в plain text - используются те же `_fit_line`, что и в
        rich-версии (одна и та же обрезка под MAX_WIDTH_TEXT_RICH_MESSAGE),
        просто "развёрнутые" в строку через `_flatten_to_plain_text`."""

        rank_line_a = _fit_line(fighter_a.name, prefix=f"Гуль {rank_a} ранга ")
        rank_line_b = _fit_line(fighter_b.name, prefix=f"Гуль {rank_b} ранга ")
        winner_line, loser_line = self._winner_lines(result, fighter_a, fighter_b)
        hp_line_a, hp_line_b = self._hp_lines(result, fighter_a, fighter_b)

        return self._dialog_service.text(
            key="battle_result_summary",
            rank_line_a=_flatten_to_plain_text(rank_line_a),
            rank_line_b=_flatten_to_plain_text(rank_line_b),
            winner_line=_flatten_to_plain_text(winner_line),
            loser_line=_flatten_to_plain_text(loser_line),
            hp_line_a=_flatten_to_plain_text(hp_line_a),
            hp_line_b=_flatten_to_plain_text(hp_line_b),
            rounds=len(result.rounds),
        )

    def _winner_lines(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> Tuple[RichLine, RichLine]:
        """Одно имя на строку - раньше было "Победитель: A. B проиграл." в
        ОДНОЙ строке с двумя именами, см. MAX_WIDTH_TEXT_RICH_MESSAGE."""

        if result.winner is None:
            draw: RichLine = ["🤝 Ничья."]
            return draw, list(draw)

        winner, loser = (
            (fighter_a, fighter_b) if result.winner == "a" else (fighter_b, fighter_a)
        )
        outcome = "повержен" if result.ended_naturally else "проиграл по итогам раундов"
        winner_line = _fit_line(winner.name, prefix="🏆 Победитель: ")
        loser_line = _fit_line(loser.name, suffix=f": {outcome}.")
        return winner_line, loser_line

    def _hp_lines(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> Tuple[RichLine, RichLine]:
        hp_line_a = _fit_line(fighter_a.name, prefix="❤️ ", suffix=f": {round(result.final_hp_a)} HP")
        hp_line_b = _fit_line(fighter_b.name, prefix="❤️ ", suffix=f": {round(result.final_hp_b)} HP")
        return hp_line_a, hp_line_b

    def _round_lines(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> List[RichLine]:
        """На раунд: разделитель, все строки "что произошло" (оба бойца,
        без чисел HP), затем ровно 2 строки "итог раунда" (по одному
        бойцу) - см. docstring модуля про то, почему именно так."""

        hp_a = fighter_a.stats.health
        hp_b = fighter_b.stats.health
        last_round_number = result.rounds[-1].round_number if result.rounds else None
        lines: List[RichLine] = []

        for round_result in result.rounds:
            lines.append([f"──── Раунд {round_result.round_number} ────"])
            lines.extend(_action_lines(fighter_a, round_result.actions_a))
            lines.extend(_action_lines(fighter_b, round_result.actions_b))

            healed_a = sum(
                a.healed for a in round_result.actions_a if isinstance(a, RegenAction)
            )
            healed_b = sum(
                a.healed for a in round_result.actions_b if isinstance(a, RegenAction)
            )
            steps_a = _build_hp_trajectory(hp_a, healed_a, round_result.damage_to_a)
            steps_b = _build_hp_trajectory(hp_b, healed_b, round_result.damage_to_b)
            hp_a, hp_b = steps_a[-1].value, steps_b[-1].value

            if round_result.round_number == last_round_number:
                # На последнем раунде честный последний шаг может быть 0/0
                # у ОБОИХ (обоюдный нокаут) - BattleResult.final_hp_* уже
                # несёт UX-подмену победителя на mutual_ko_winner_hp (2.6).
                # Не-мутуал-КО случаи здесь ничего не меняют - final_hp_*
                # и так совпадает с честным значением, замена молча no-op.
                steps_a = _apply_mutual_ko_display(steps_a, result.final_hp_a)
                steps_b = _apply_mutual_ko_display(steps_b, result.final_hp_b)

            lines.append(_fighter_outcome_line(fighter_a, steps_a))
            lines.append(_fighter_outcome_line(fighter_b, steps_b))

        return lines


__all__ = ["BattleTextGenerator", "MAX_WIDTH_TEXT_RICH_MESSAGE"]
