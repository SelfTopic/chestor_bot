from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple

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

from src.bot.dialogs import Dialogs, Line
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


# Вместо имени в фразу подставляется маркер: по нему строка режется на prefix/suffix, и
# _fit_line обрезает только имя, а не текст фразы.
NAME = "\x00"

HpCause = Literal["regen", "damage"]


@dataclass(frozen=True)
class _HpStep:
    value: float
    delta: Optional[float] = None
    cause: Optional[HpCause] = None


def _build_hp_trajectory(hp_before: float, healed: float, damage: float) -> List[_HpStep]:
    steps = [_HpStep(value=hp_before)]
    current = hp_before
    if healed > 0:
        current = current + healed
        steps.append(_HpStep(value=current, delta=healed, cause="regen"))
    if damage > 0:
        current = max(0.0, current - damage)
        steps.append(_HpStep(value=current, delta=-damage, cause="damage"))
    return steps


def _apply_mutual_ko_display(steps: List[_HpStep], final_hp: float) -> List[_HpStep]:
    if not steps or steps[-1].value == final_hp:
        return steps
    return steps[:-1] + [_HpStep(value=final_hp)]


LOG = Dialogs.fight.log


class BattleTextGenerator:
    def __init__(self, dialog_service: DialogService) -> None:
        self._dialog_service = dialog_service

    def _text(self, line: Line) -> str:
        return self._dialog_service.text(line)

    def _named(self, line: Line, name: str) -> RichLine:
        prefix, marker, suffix = self._text(line).partition(NAME)
        if not marker:
            return [prefix]
        return _fit_line(name, prefix=prefix, suffix=suffix)

    def _hit_line(self, name: str, hit: HitResult, is_fast: bool) -> RichLine:
        if not hit.landed or hit.attack_type is None:
            icon = "⚡💨" if is_fast else "💨"
            line = (
                LOG.fast_miss(icon=icon, name=NAME)
                if is_fast
                else LOG.miss(icon=icon, name=NAME)
            )
        elif round(hit.damage) <= 0:
            line = LOG.blocked(icon="⚡🛡️" if is_fast else "🛡️", name=NAME)
        else:
            icon = _HIT_ICON[hit.attack_type]
            damage = round(hit.damage)
            line = (
                LOG.fast_hit(icon=f"⚡{icon}", name=NAME, damage=damage)
                if is_fast
                else LOG.hit(icon=icon, name=NAME, damage=damage)
            )
        return self._named(line, name)

    def _action_line(self, name: str, action: RoundAction) -> Optional[RichLine]:
        if isinstance(action, RegenAction):
            healed = round(action.healed)
            line = (
                LOG.regen(name=NAME, healed=healed)
                if healed > 0
                else LOG.regen_nothing(name=NAME)
            )
            return self._named(line, name)
        if isinstance(action, AttackAction):
            return self._hit_line(name, action.hit, is_fast=False)
        if isinstance(action, FastAttackAction):
            return self._hit_line(name, action.hit, is_fast=True)
        if isinstance(action, (DefenseAction, IdleAction)):
            return None
        raise NotImplementedError(f"Неизвестный тип действия для рендера: {type(action)!r}")

    def _action_lines(self, fighter: Fighter, actions: List[RoundAction]) -> List[RichLine]:
        lines = (self._action_line(fighter.name, action) for action in actions)
        return [line for line in lines if line is not None]

    def _hp_chain(self, steps: List[_HpStep]) -> str:
        if len(steps) == 1:
            return self._text(LOG.hp_unchanged(hp=round(steps[0].value)))

        parts = [str(round(steps[0].value))]
        for step in steps[1:]:
            hp = round(step.value)
            delta = round(step.delta or 0.0)
            if step.cause == "damage":
                line = LOG.hp_damage(hp=hp, damage=-delta) if delta else LOG.hp_blocked(hp=hp)
            elif step.cause == "regen":
                line = LOG.hp_regen(hp=hp, healed=delta) if delta else LOG.hp_weak_regen(hp=hp)
            else:
                parts.append(str(hp))
                continue
            parts.append(self._text(line))
        return " → ".join(parts) + " HP"

    def _fighter_outcome_line(self, fighter: Fighter, steps: List[_HpStep]) -> RichLine:
        chain = self._hp_chain(steps)
        line = (
            LOG.hp_defeated(name=NAME, chain=chain)
            if steps[-1].value <= 0
            else LOG.hp(name=NAME, chain=chain)
        )
        return self._named(line, fighter.name)

    def _rank_line(self, fighter: Fighter, rank: str) -> RichLine:
        return self._named(Dialogs.fight.rank(rank=rank, name=NAME), fighter.name)

    def build_rich_message(
        self,
        result: BattleResult,
        fighter_a: Fighter,
        fighter_b: Fighter,
        rank_a: str,
        rank_b: str,
    ) -> InputRichMessage:
        winner_line, loser_line = self._winner_lines(result, fighter_a, fighter_b)
        hp_line_a, hp_line_b = self._hp_lines(result, fighter_a, fighter_b)

        blocks: List[InputRichBlock] = [
            InputRichBlockSectionHeading(text=self._text(Dialogs.fight.title()), size=3),
            InputRichBlockParagraph(text=self._rank_line(fighter_a, rank_a)),
            InputRichBlockParagraph(text=self._text(Dialogs.fight.versus())),
            InputRichBlockParagraph(text=self._rank_line(fighter_b, rank_b)),
        ]

        if result.rounds:
            blocks.append(
                InputRichBlockDetails(
                    summary=self._text(Dialogs.fight.rounds_title(count=len(result.rounds))),
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
        winner_line, loser_line = self._winner_lines(result, fighter_a, fighter_b)
        hp_line_a, hp_line_b = self._hp_lines(result, fighter_a, fighter_b)

        return self._dialog_service.text(
            Dialogs.fight.summary(
                rank_line_a=_flatten_to_plain_text(self._rank_line(fighter_a, rank_a)),
                rank_line_b=_flatten_to_plain_text(self._rank_line(fighter_b, rank_b)),
                winner_line=_flatten_to_plain_text(winner_line),
                loser_line=_flatten_to_plain_text(loser_line),
                hp_line_a=_flatten_to_plain_text(hp_line_a),
                hp_line_b=_flatten_to_plain_text(hp_line_b),
                rounds=len(result.rounds),
            )
        )

    def _winner_lines(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> Tuple[RichLine, RichLine]:
        if result.winner is None:
            draw: RichLine = [self._text(Dialogs.fight.draw())]
            return draw, list(draw)

        winner, loser = (
            (fighter_a, fighter_b) if result.winner == "a" else (fighter_b, fighter_a)
        )
        loser_phrase = (
            Dialogs.fight.defeated(name=NAME)
            if result.ended_naturally
            else Dialogs.fight.lost_on_rounds(name=NAME)
        )
        winner_line = self._named(Dialogs.fight.winner(name=NAME), winner.name)
        loser_line = self._named(loser_phrase, loser.name)
        return winner_line, loser_line

    def _hp_lines(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> Tuple[RichLine, RichLine]:
        hp_line_a = self._named(
            Dialogs.fight.final_hp(name=NAME, hp=round(result.final_hp_a)), fighter_a.name
        )
        hp_line_b = self._named(
            Dialogs.fight.final_hp(name=NAME, hp=round(result.final_hp_b)), fighter_b.name
        )
        return hp_line_a, hp_line_b

    def _round_lines(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> List[RichLine]:
        hp_a = fighter_a.stats.health
        hp_b = fighter_b.stats.health
        last_round_number = result.rounds[-1].round_number if result.rounds else None
        lines: List[RichLine] = []

        for round_result in result.rounds:
            lines.append([self._text(LOG.round(number=round_result.round_number))])
            lines.extend(self._action_lines(fighter_a, round_result.actions_a))
            lines.extend(self._action_lines(fighter_b, round_result.actions_b))

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

            lines.append(self._fighter_outcome_line(fighter_a, steps_a))
            lines.append(self._fighter_outcome_line(fighter_b, steps_b))

        return lines


__all__ = ["BattleTextGenerator", "MAX_WIDTH_TEXT_RICH_MESSAGE"]
