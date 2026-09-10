"""Оркестрация всего боя - класс Battle. См. BATTLE_ENGINE.md часть 0/2.6
и REGENERATION.md для причин, почему раунд устроен именно так."""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import List, Optional

from ....game_configs import BATTLE_CONFIG
from .actions import AttackAction, FastAttackAction, RegenAction, RoundAction, RoundActionType
from .fighter import EffectiveStats, Fighter
from .formulas import compress_stat_advantage, resolve_extra_hit_counts
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
        compress_hp: bool = True,
    ) -> None:
        """`compress_hp=False` - сильная сторона дерётся ВСЕРЬЁЗ: HP-пул не
        сжимается относительно соперника (сжатие остальных статов в
        формулах - урон/хил/уклонение/гейт/лишний удар - остаётся всегда,
        оно невидимо игроку). Это осознанный выбор игрока при перевесе 2x+
        (см. BATTLE_ENGINE.md 1.5) - "драться не в полную силу без согласия
        игрока нельзя". Безопасный дефолт True: бои с мобами, дуэли при
        перевесе <2x и таймаут ответа - всегда с форой (сжатым HP)."""

        self.fighter_a = fighter_a
        self.fighter_b = fighter_b
        if compress_hp:
            self._compress_hp_pools()
        self.max_rounds = max_rounds if max_rounds is not None else BATTLE_CONFIG.max_rounds
        self.rounds: List[RoundResult] = []
        self._round_number = 0
        self._finished = False
        # HP ДО последнего сыгранного раунда - нужно для тай-брейка при
        # одновременном обоюдном нокауте (2.6). ПОСЛЕ _compress_hp_pools -
        # тай-брейк должен работать со сжатым HP, как и весь остальной бой.
        self._hp_a_before_last = fighter_a.current_hp
        self._hp_b_before_last = fighter_b.current_hp

    def _compress_hp_pools(self) -> None:
        """"Кривая перевеса силы" (см. чат) - health оказался единственным
        боевым статом, который не проходит ни через одну формулу с
        _compress_ratio (dodge/gate/extra_hit/raw_damage сравнивают статы
        атакующего и защищающегося прямо в момент удара) - он просто задаёт
        размер HP-пула напрямую. По симуляции это САМЫЙ крутой канал в
        одиночку (health x1.5 при равенстве всех остальных статов уже давал
        ~97% побед) - без сжатия здесь весь остальной рефакторинг формул не
        достаточен, чтобы кривая легла на целевые точки (2x -> 75%).

        Применяется здесь, а не в compute_effective_stats - только Battle
        знает ОБОИХ бойцов сразу, а сжатие по дизайну "относительно
        конкретного соперника В ЭТОМ бою" (не от абстрактной константы).

        Слабый остаётся якорем БЕЗ ИЗМЕНЕНИЙ, сильный подтягивается к нему
        (compress_stat_advantage) - та же схема, что и у raw_damage/
        apply_heal. Сохраняет ДОЛЮ уже нанесённого урона (current_hp/
        old_health), а не просто перезаписывает current_hp - иначе Battle,
        обёрнутый вокруг уже повреждённого Fighter (см.
        battle_engine_round_test.py, где тесты бьют fighter.take_damage()
        ДО создания Battle, чтобы подготовить конкретный HP для одного
        раунда), стирал бы этот урон."""

        health_a = self.fighter_a.stats.health
        health_b = self.fighter_b.stats.health
        compressed_a = compress_stat_advantage(health_a, health_b)
        compressed_b = compress_stat_advantage(health_b, health_a)

        for fighter, old_health, new_health in (
            (self.fighter_a, health_a, compressed_a),
            (self.fighter_b, health_b, compressed_b),
        ):
            fraction_remaining = fighter.current_hp / old_health if old_health > 0 else 0.0
            fighter.stats = replace(fighter.stats, health=new_health)
            fighter.current_hp = new_health * fraction_remaining

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
            healed = fighter.apply_heal(opponent, rng)
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
            hit = resolve_hit(fighter, opponent, rng, is_fast_attack=True)
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

            # UX-находка (см. чат): показывать "0 против 0" при обоюдном
            # нокауте нечестно выглядит для игрока - реальное правило
            # тай-брейка (см. выше) невидимо, а голые нули читаются как
            # необъяснённая монетка. Победитель показывается с 1 HP вместо
            # 0 - тот же принцип, что и у проигравшего после ВСЕГО боя
            # (3.1, "не 0, а 1 HP"), просто здесь применяется прямо в
            # движке для этого конкретного случая. Настоящая ничья (winner
            # is None) не трогается - бумпить нечего.
            if winner == "a":
                hp_a = BATTLE_CONFIG.mutual_ko_winner_hp
            elif winner == "b":
                hp_b = BATTLE_CONFIG.mutual_ko_winner_hp
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
