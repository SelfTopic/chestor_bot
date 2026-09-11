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
анимации, - которому те же хелперы тоже понадобятся)."""

from __future__ import annotations

from typing import List, Tuple

from aiogram.types import (
    InputRichBlockDetails,
    InputRichBlockList,
    InputRichBlockListItem,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockUnion,
    InputRichMessage,
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
    RoundResult,
)

_HIT_ICON = {AttackType.PHYSICAL: "👊", AttackType.KAGUNE: "🦑"}

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
) -> str:
    """Собирает `{prefix}{name}{suffix}`, обрезая ИМЕННО name (а не konец
    строки вслепую) так, чтобы вся строка целиком не превышала max_width -
    prefix/suffix (иконки, HP, счётчики) всегда остаются целыми, это они
    несут игровую информацию, обрезать есть смысл только переменную по
    длине часть (имя)."""

    fixed_width = len((prefix + suffix).replace(" ", ""))
    name_budget = max(1, max_width - fixed_width)
    return f"{prefix}{_truncate_to_width(name, name_budget)}{suffix}"


def _format_hit(hit: HitResult) -> str:
    # attack_type всегда заполнен при landed=True (см. hit.py) - вторая
    # часть условия защищает только pyright (Optional), реального
    # landed=True + attack_type=None не бывает.
    if not hit.landed or hit.attack_type is None:
        return "💨 промах"
    return f"{_HIT_ICON[hit.attack_type]} {round(hit.damage)}"


def _format_action(action: RoundAction) -> str:
    if isinstance(action, AttackAction):
        return _format_hit(action.hit)
    if isinstance(action, FastAttackAction):
        return "⚡" + _format_hit(action.hit)
    if isinstance(action, RegenAction):
        return f"💊 +{round(action.healed)}"
    if isinstance(action, (DefenseAction, IdleAction)):
        # Зарезервированы (actions.py) - decide_action их пока никогда не
        # возвращает, но рендерер не должен упасть, если это изменится
        # без обновления этого файла.
        return "—"
    raise NotImplementedError(f"Неизвестный тип действия для рендера: {type(action)!r}")


class BattleTextGenerator:
    """Требует `Fighter` для ОБЕИХ сторон отдельно от `BattleResult` -
    `BattleResult.stats_a/stats_b` это голые `EffectiveStats` без имени/id
    (см. чат), имя живёт только на `Fighter.name`/`FighterSnapshot.name`."""

    def __init__(self, dialog_service: DialogService) -> None:
        self._dialog_service = dialog_service

    def build_rich_message(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> InputRichMessage:
        winner_line, loser_line = self._winner_lines(result, fighter_a, fighter_b)
        hp_line_a, hp_line_b = self._hp_lines(result, fighter_a, fighter_b)

        blocks: List[InputRichBlockUnion] = [
            # Без имён в заголовке - "A vs B" в одной строке имеет ту же
            # проблему переноса, что и раунды, а заголовок обрезать некрасиво.
            InputRichBlockSectionHeading(text="⚔️ Итоги боя", size=3),
            InputRichBlockParagraph(text=winner_line),
            InputRichBlockParagraph(text=loser_line),
            InputRichBlockParagraph(text=hp_line_a),
            InputRichBlockParagraph(text=hp_line_b),
        ]

        if result.rounds:
            blocks.append(
                InputRichBlockDetails(
                    summary=f"📜 Ход боя ({len(result.rounds)} раунд(ов))",
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

        return InputRichMessage(blocks=blocks)

    def build_plain_text(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> str:
        """Фолбэк на случай, если `answer_rich` недоступен (см.
        race_profile_router.py - тот же паттерн try/except TelegramAPIError).
        Намеренно БЕЗ раундов - в отличие от rich-версии, здесь их некуда
        свернуть, а бой может идти 20-30 раундов; полный лог только в
        rich-сообщении, тут - голая сводка. Каждая строка уже обрезана под
        MAX_WIDTH_TEXT_RICH_MESSAGE - шаблон в dialogs.json просто их
        склеивает переносами строк, не комбинируя два имени в одной."""

        winner_line, loser_line = self._winner_lines(result, fighter_a, fighter_b)
        hp_line_a, hp_line_b = self._hp_lines(result, fighter_a, fighter_b)

        return self._dialog_service.text(
            key="battle_result_summary",
            winner_line=winner_line,
            loser_line=loser_line,
            hp_line_a=hp_line_a,
            hp_line_b=hp_line_b,
            rounds=len(result.rounds),
        )

    def _winner_lines(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> Tuple[str, str]:
        """Одно имя на строку - раньше было "Победитель: A. B проиграл." в
        ОДНОЙ строке с двумя именами, см. MAX_WIDTH_TEXT_RICH_MESSAGE."""

        if result.winner is None:
            draw = "🤝 Ничья."
            return draw, draw

        winner, loser = (
            (fighter_a, fighter_b) if result.winner == "a" else (fighter_b, fighter_a)
        )
        outcome = "повержен" if result.ended_naturally else "проиграл по итогам раундов"
        winner_line = _fit_line(winner.name, prefix="🏆 Победитель: ")
        loser_line = _fit_line(loser.name, suffix=f": {outcome}.")
        return winner_line, loser_line

    def _hp_lines(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> Tuple[str, str]:
        hp_line_a = _fit_line(fighter_a.name, prefix="❤️ ", suffix=f": {round(result.final_hp_a)} HP")
        hp_line_b = _fit_line(fighter_b.name, prefix="❤️ ", suffix=f": {round(result.final_hp_b)} HP")
        return hp_line_a, hp_line_b

    def _round_lines(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> List[str]:
        """Два элемента списка на раунд (по одному на бойца), не один
        комбинированный - та же причина, что у _winner_lines/_hp_lines."""

        hp_a = fighter_a.stats.health
        hp_b = fighter_b.stats.health
        last_round_number = result.rounds[-1].round_number if result.rounds else None
        lines: List[str] = []

        for round_result in result.rounds:
            hp_a, hp_b = self._apply_round_hp_change(round_result, hp_a, hp_b)
            display_hp_a, display_hp_b = hp_a, hp_b

            if round_result.round_number == last_round_number:
                # На последнем раунде честные hp_a/hp_b могут быть 0/0
                # (обоюдный нокаут) - BattleResult.final_hp_* уже несёт
                # UX-подмену победителя на mutual_ko_winner_hp (2.6),
                # переиспользуем её тут же, иначе лог покажет "0 против 0" -
                # ровно ту путаницу, которую 2.6 и должна была убрать.
                display_hp_a, display_hp_b = result.final_hp_a, result.final_hp_b

            prefix = f"Р{round_result.round_number} · "
            lines.append(
                self._fit_action_line(prefix, fighter_a, round_result.actions_a, display_hp_a)
            )
            lines.append(
                self._fit_action_line(prefix, fighter_b, round_result.actions_b, display_hp_b)
            )

        return lines

    @staticmethod
    def _fit_action_line(
        prefix: str, fighter: Fighter, actions: List[RoundAction], hp: float
    ) -> str:
        actions_str = " ".join(_format_action(a) for a in actions) or "—"
        suffix = f": {actions_str} ({round(hp)} HP)"
        return _fit_line(fighter.name, prefix=prefix, suffix=suffix)

    @staticmethod
    def _apply_round_hp_change(
        round_result: RoundResult, hp_a: float, hp_b: float
    ) -> "tuple[float, float]":
        """Урон - НЕ единственное, что меняет HP за раунд: RegenAction
        лечит в тот же раунд (Fighter.apply_heal уже применяется ДО того,
        как в _play_one_round применяется очередь урона). Раньше здесь
        учитывался только damage_to_a/b - раунд с регенерацией показывал
        заниженный (иногда буквально "0 HP") HP, хотя боец на самом деле
        вылечился. Found через scripts/battle_text_demo.py (см. чат)."""

        healed_a = sum(a.healed for a in round_result.actions_a if isinstance(a, RegenAction))
        healed_b = sum(a.healed for a in round_result.actions_b if isinstance(a, RegenAction))
        return (
            max(0.0, hp_a + healed_a - round_result.damage_to_a),
            max(0.0, hp_b + healed_b - round_result.damage_to_b),
        )


__all__ = ["BattleTextGenerator", "MAX_WIDTH_TEXT_RICH_MESSAGE"]
