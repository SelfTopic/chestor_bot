"""Оркестрация всего боя - класс Battle. См. BATTLE_ENGINE.md часть 0/2.6
и REGENERATION.md для причин, почему раунд устроен именно так."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

from ....game_configs import BATTLE_CONFIG
from .actions import AttackAction, FastAttackAction, RegenAction, RoundAction, RoundActionType
from .fighter import EffectiveStats, Fighter
from .formulas import resolve_extra_hit_counts
from .hit import resolve_hit
from .round import RoundResult

_default_rng = random.Random()


@dataclass(frozen=True)
class BattleResult:
    rounds: List[RoundResult]
    winner: Optional[str]  # "a" | "b" | None (истинная ничья, тай-брейк не спас)
    ended_naturally: bool  # True - кто-то дошёл до 0 HP раньше MAX_ROUNDS
    final_hp_a: float
    final_hp_b: float
    stats_a: EffectiveStats
    stats_b: EffectiveStats


class Battle:
    """Оба бойца действуют одновременно каждый раунд (2.1). Валидация
    статов происходит раньше - в конструкторе Fighter, не здесь.

    Поддерживает и пошаговую игру (`play_round()` - для будущей
    поштучной анимации в Telegram), и разовый прогон (`run()`)."""

    def __init__(
        self,
        fighter_a: Fighter,
        fighter_b: Fighter,
        max_rounds: Optional[int] = None,
    ) -> None:
        self.fighter_a = fighter_a
        self.fighter_b = fighter_b
        self.max_rounds = max_rounds if max_rounds is not None else BATTLE_CONFIG.max_rounds
        self.rounds: List[RoundResult] = []
        self._round_number = 0
        self._finished = False
        # HP ДО последнего сыгранного раунда - нужно для тай-брейка при
        # одновременном обоюдном нокауте (2.6).
        self._hp_a_before_last = fighter_a.current_hp
        self._hp_b_before_last = fighter_b.current_hp

    @property
    def is_finished(self) -> bool:
        return self._finished or self._round_number >= self.max_rounds

    def play_round(self, rng: random.Random = _default_rng) -> RoundResult:
        if self._finished:
            raise RuntimeError("Battle already finished - can't play another round")

        self._round_number += 1
        self._hp_a_before_last = self.fighter_a.current_hp
        self._hp_b_before_last = self.fighter_b.current_hp

        result = self._play_one_round(self._round_number, rng)
        self.rounds.append(result)

        if self.fighter_a.is_defeated or self.fighter_b.is_defeated:
            self._finished = True

        return result

    def run(self, rng: random.Random = _default_rng) -> BattleResult:
        while not self.is_finished:
            self.play_round(rng)
        return self._build_result()

    def _play_one_round(self, round_number: int, rng: random.Random) -> RoundResult:
        # Снимок "гарантия ещё не использована" ДО decide_action - иначе
        # не отличить, каким проком (гарантированным или вероятностным)
        # обернулась вернувшаяся RoundActionType.REGEN, см. REGENERATION.md.
        a_guaranteed_available = not self.fighter_a.regen_guaranteed_used
        b_guaranteed_available = not self.fighter_b.regen_guaranteed_used

        action_a_type = self.fighter_a.decide_action(self.fighter_b, rng)
        action_b_type = self.fighter_b.decide_action(self.fighter_a, rng)

        extra_a, extra_b = resolve_extra_hit_counts(
            self.fighter_a.stats.speed, self.fighter_b.stats.speed, rng
        )

        actions_a, damage_to_b = self._resolve_participant(
            self.fighter_a, self.fighter_b, action_a_type, a_guaranteed_available, extra_a, rng
        )
        actions_b, damage_to_a = self._resolve_participant(
            self.fighter_b, self.fighter_a, action_b_type, b_guaranteed_available, extra_b, rng
        )

        self.fighter_a.take_damage(damage_to_a)
        self.fighter_b.take_damage(damage_to_b)

        return RoundResult(
            round_number=round_number,
            actions_a=actions_a,
            actions_b=actions_b,
            damage_to_a=damage_to_a,
            damage_to_b=damage_to_b,
        )

    def _resolve_participant(
        self,
        fighter: Fighter,
        opponent: Fighter,
        action_type: RoundActionType,
        guaranteed_was_available: bool,
        extra_hits: int,
        rng: random.Random,
    ) -> "tuple[List[RoundAction], float]":
        """Основное действие (Attack ИЛИ Regen) + ноль-два бонусных
        FastAttack от speed - бонусные удары случаются НЕЗАВИСИМО от
        основного действия (REGENERATION.md: "быстрый гуль после
        регенерации ещё и может успеть ударить")."""

        actions: List[RoundAction] = []
        damage_dealt = 0.0

        if action_type is RoundActionType.REGEN:
            healed = fighter.apply_heal(rng)
            actions.append(RegenAction(healed=healed, was_guaranteed=guaranteed_was_available))
        elif action_type is RoundActionType.ATTACK:
            hit = resolve_hit(fighter, opponent, rng)
            actions.append(AttackAction(hit=hit))
            damage_dealt += hit.damage
        else:
            # DEFENSE/IDLE зарезервированы (actions.py) - decide_action их
            # пока никогда не возвращает. Громкая ошибка вместо тихого
            # неверного поведения, если это когда-нибудь изменится без
            # обновления этой функции.
            raise NotImplementedError(f"RoundActionType {action_type} ещё не реализован")

        for _ in range(extra_hits):
            hit = resolve_hit(fighter, opponent, rng)
            actions.append(FastAttackAction(hit=hit))
            damage_dealt += hit.damage

        return actions, damage_dealt

    def _build_result(self) -> BattleResult:
        hp_a, hp_b = self.fighter_a.current_hp, self.fighter_b.current_hp
        ended_naturally = self.fighter_a.is_defeated or self.fighter_b.is_defeated

        if self.fighter_a.is_defeated and self.fighter_b.is_defeated:
            # 2.6 - одновременный обоюдный нокаут, тай-брейк не был решён
            # явно в доке. Рабочее правило: побеждает тот, у кого HP ДО
            # последнего обмена было выше; если и тут ничья - настоящая
            # ничья (None).
            if self._hp_a_before_last > self._hp_b_before_last:
                winner: Optional[str] = "a"
            elif self._hp_b_before_last > self._hp_a_before_last:
                winner = "b"
            else:
                winner = None
        elif self.fighter_a.is_defeated:
            winner = "b"
        elif self.fighter_b.is_defeated:
            winner = "a"
        else:
            # MAX_ROUNDS кончились без естественного конца - решает остаток HP.
            if hp_a > hp_b:
                winner = "a"
            elif hp_b > hp_a:
                winner = "b"
            else:
                winner = None

        return BattleResult(
            rounds=self.rounds,
            winner=winner,
            ended_naturally=ended_naturally,
            final_hp_a=hp_a,
            final_hp_b=hp_b,
            stats_a=self.fighter_a.stats,
            stats_b=self.fighter_b.stats,
        )


__all__ = ["BattleResult", "Battle"]
