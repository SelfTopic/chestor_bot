import random
from dataclasses import dataclass, field
from typing import Optional

from src.bot.services.battle.models import BattleEvent, BattleFighter
from src.bot.types import KaguneType

MAX_ROUNDS = 20
REGEN_THRESHOLD = 0.25


@dataclass
class BattleResult:
    winner: Optional[BattleFighter]
    loser: Optional[BattleFighter]
    rounds: int
    events: list[BattleEvent] = field(default_factory=list)
    is_draw: bool = False


class BattleMechanics:
    KAGUNE_ATK = {
        KaguneType.UKAKU: 1.4,
        KaguneType.KOUKAKU: 1.6,
        KaguneType.RINKAKU: 1.8,
        KaguneType.BIKAKU: 2.0,
    }

    # Защитный множитель — обратный атакующему чтобы коукаку был живучее
    KAGUNE_DEF = {
        KaguneType.UKAKU: 0.75,
        KaguneType.KOUKAKU: 1.3,
        KaguneType.RINKAKU: 0.85,
        KaguneType.BIKAKU: 1.0,
    }

    def _calculate_damage(
        self, attacker: BattleFighter, defender: BattleFighter, is_crit: bool
    ) -> int:
        raw = (
            attacker.strength * 0.8 + attacker.kagune_strength * 1.2
        ) * self.KAGUNE_ATK[attacker.kagune_type]

        raw *= random.uniform(0.85, 1.15)

        if is_crit:
            raw *= 2.0

        defense = (
            defender.strength * 0.3 + defender.kagune_strength * 0.5
        ) * self.KAGUNE_DEF[defender.kagune_type]

        return max(1, int(raw - defense))

    def _roll_event_type(
        self,
        attacker: BattleFighter,
        defender: BattleFighter,
    ) -> str:
        total_speed = attacker.speed + defender.speed
        total_dex = attacker.dexterity + defender.dexterity

        miss_chance = defender.speed / total_speed * 0.15
        block_chance = (
            defender.dexterity
            / total_dex
            * 0.15
            * self.KAGUNE_DEF[defender.kagune_type]
        )
        crit_chance = attacker.dexterity / total_dex * 0.15

        roll = random.random()

        if roll < miss_chance:
            return "miss"
        roll -= miss_chance

        if roll < block_chance:
            return "block"
        roll -= block_chance

        if roll < crit_chance:
            return "crit"

        return "hit"

    def _make_round(
        self, attacker: BattleFighter, defender: BattleFighter
    ) -> BattleEvent:
        event_type = self._roll_event_type(attacker, defender)

        if event_type == "miss":
            damage = 0
        elif event_type == "block":
            damage = max(
                1, int(self._calculate_damage(attacker, defender, False) * 0.4)
            )
        else:
            damage = self._calculate_damage(
                attacker, defender, is_crit=(event_type == "crit")
            )

        hp_before = defender.hp
        defender.hp = max(0, defender.hp - damage)

        return BattleEvent(
            type=event_type,
            attacker=attacker,
            defender=defender,
            damage=damage,
            defender_hp_before=hp_before,
            defender_hp_after=defender.hp,
            attacker_hp_snapshot=attacker.hp,
            hp_delta_attacker=0,
            hp_delta_defender=-damage,
        )

    def _check_regen(
        self, fighter: BattleFighter, opponent: BattleFighter
    ) -> Optional[BattleEvent]:
        if fighter.regen_used:
            return None
        if fighter.hp > fighter.max_hp * REGEN_THRESHOLD:
            return None

        regen_amount = fighter.regeneration * 10
        atk_hp_before = fighter.hp
        fighter.hp = min(fighter.max_hp, fighter.hp + regen_amount)
        fighter.regen_used = True

        event_type = self._roll_event_type(fighter, opponent)
        damage = (
            0
            if event_type == "miss"
            else self._calculate_damage(
                fighter, opponent, is_crit=(event_type == "crit")
            )
        )

        def_hp_before = opponent.hp
        opponent.hp = max(0, opponent.hp - damage)

        return BattleEvent(
            type="regen",
            attacker=fighter,
            defender=opponent,
            damage=damage,
            defender_hp_before=def_hp_before,
            defender_hp_after=opponent.hp,
            attacker_hp_before=atk_hp_before,
            attacker_hp_after=fighter.hp,
        )

    def simulate(
        self,
        fighter_left: BattleFighter,
        fighter_right: BattleFighter,
    ) -> BattleResult:
        events: list[BattleEvent] = []
        round_num = 0

        # Определяем порядок хода, НЕ меняя стороны
        if fighter_right.speed > fighter_left.speed:
            first = fighter_right
            second = fighter_left
        else:
            first = fighter_left
            second = fighter_right

        while fighter_left.hp > 0 and fighter_right.hp > 0 and round_num < MAX_ROUNDS:
            round_num += 1

            # Первый ходит
            events.append(self._make_round(first, second))
            if fighter_left.hp <= 0 or fighter_right.hp <= 0:
                break

            regen = self._check_regen(second, first)
            if regen:
                events.append(regen)
            if fighter_left.hp <= 0 or fighter_right.hp <= 0:
                break

            # Второй ходит
            events.append(self._make_round(second, first))
            if fighter_left.hp <= 0 or fighter_right.hp <= 0:
                break

            regen = self._check_regen(first, second)
            if regen:
                events.append(regen)

        # Определение победителя
        if fighter_left.hp > 0 and fighter_right.hp <= 0:
            winner = fighter_left
            loser = fighter_right
            is_draw = False
        elif fighter_right.hp > 0 and fighter_left.hp <= 0:
            winner = fighter_right
            loser = fighter_left
            is_draw = False
        else:
            is_draw = True
            if fighter_left.hp >= fighter_right.hp:
                winner = fighter_left
                loser = fighter_right
            else:
                winner = fighter_right
                loser = fighter_left

        return BattleResult(
            winner=winner,
            loser=loser,
            rounds=round_num,
            events=events,
            is_draw=is_draw,
        )
