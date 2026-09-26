from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from selfrot.types import (
    InputRichBlock,
    InputRichBlockDetails,
    InputRichBlockDivider,
    InputRichBlockList,
    InputRichBlockListItem,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichMessage,
    RichText,
    RichTextBold,
)

from src.bot.services.battle_engine.core import (
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
from src.bot.services.dialog import DialogService

_HIT_ICON = {AttackType.PHYSICAL: "👊", AttackType.KAGUNE: "♦️"}

MAX_WIDTH_TEXT_RICH_MESSAGE = 54

# Алиас на RichText, а не List[...]: list в pyright инвариантен, и узкий список не проходит
# проверку под рекурсивный RichText.
RichLine = RichText


def _truncate_to_width(text: str, max_width: int) -> str:
    if len(text.replace(" ", "")) <= max_width:
        return text

    # «…» тоже занимает единицу бюджета.
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
    fixed_width = len((prefix + suffix).replace(" ", ""))
    name_budget = max(1, max_width - fixed_width)
    fitted_name = _truncate_to_width(name, name_budget)
    return [prefix, RichTextBold(text=fitted_name), suffix]


def _flatten_to_plain_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_flatten_to_plain_text(item) for item in value)
    if isinstance(value, RichTextBold):
        return _flatten_to_plain_text(value.text)
    raise TypeError(f"Не умею превращать {type(value)!r} в plain text")


def _hit_verb_and_icon(hit: HitResult, is_fast: bool) -> Tuple[str, str]:
    if not hit.landed or hit.attack_type is None:
        icon = "⚡💨" if is_fast else "💨"
        verb = "не успевает ударить ещё раз" if is_fast else "промахивается"
        return icon, verb

    if round(hit.damage) <= 0:
        icon = "⚡🛡️" if is_fast else "🛡️"
        return icon, "не пробивает защиту"

    base_icon = _HIT_ICON[hit.attack_type]
    icon = f"⚡{base_icon}" if is_fast else base_icon
    verb = "успевает ударить ещё раз" if is_fast else "наносит удар"
    return icon, f"{verb} — {round(hit.damage)} урона"


def _action_icon_and_text(action: RoundAction) -> "Optional[Tuple[str, str]]":
    if isinstance(action, RegenAction):
        if round(action.healed) <= 0:
            return "💊", "регенерирует, но почти не восстанавливает HP"
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


@dataclass(frozen=True)
class _HpStep:
    value: float
    delta: Optional[float] = None
    cause: Optional[str] = None


def _build_hp_trajectory(hp_before: float, healed: float, damage: float) -> List[_HpStep]:
    steps = [_HpStep(value=hp_before)]
    current = hp_before
    if healed > 0:
        current = current + healed
        steps.append(_HpStep(value=current, delta=healed, cause="регенерация"))
    if damage > 0:
        current = max(0.0, current - damage)
        steps.append(_HpStep(value=current, delta=-damage, cause="урон"))
    return steps


_ZERO_DELTA_LABEL = {"урон": "не пробил", "регенерация": "почти не помогла"}


def _format_hp_chain(steps: List[_HpStep]) -> str:
    if len(steps) == 1:
        return f"{round(steps[0].value)} HP (без изменений)"

    parts = [str(round(steps[0].value))]
    for step in steps[1:]:
        if step.cause is None:
            parts.append(str(round(step.value)))
            continue

        delta = step.delta or 0.0
        if round(delta) == 0:
            label = _ZERO_DELTA_LABEL.get(step.cause, step.cause)
            parts.append(f"{round(step.value)} ({label})")
            continue

        sign = "+" if delta >= 0 else ""
        parts.append(f"{round(step.value)} ({sign}{round(delta)} {step.cause})")
    return " → ".join(parts) + " HP"


def _fighter_outcome_line(fighter: Fighter, steps: List[_HpStep]) -> RichLine:
    is_defeated = steps[-1].value <= 0
    prefix = "💀 " if is_defeated else "❤️ "
    suffix = f": {_format_hp_chain(steps)}" + (" — повержен" if is_defeated else "")
    return _fit_line(fighter.name, prefix=prefix, suffix=suffix)


def _apply_mutual_ko_display(steps: List[_HpStep], final_hp: float) -> List[_HpStep]:
    if not steps or steps[-1].value == final_hp:
        return steps
    return steps[:-1] + [_HpStep(value=final_hp)]


class BattleTextGenerator:
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

        blocks: List[InputRichBlock] = [
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
                steps_a = _apply_mutual_ko_display(steps_a, result.final_hp_a)
                steps_b = _apply_mutual_ko_display(steps_b, result.final_hp_b)

            lines.append(_fighter_outcome_line(fighter_a, steps_a))
            lines.append(_fighter_outcome_line(fighter_b, steps_b))

        return lines


__all__ = ["BattleTextGenerator", "MAX_WIDTH_TEXT_RICH_MESSAGE"]
