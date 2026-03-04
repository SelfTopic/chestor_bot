from typing import List

from src.bot.services.battle.mechanics import BattleResult
from src.bot.services.battle.models import (
    BattleFighter,
    TimelineEvent,
    TimelineEventData,
)


class BattleTimelineBuilder:
    def build(
        self,
        left: BattleFighter,
        right: BattleFighter,
        result: BattleResult,
    ) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []

        left_hp = left.max_hp
        right_hp = right.max_hp

        events.append(
            TimelineEvent(
                type="intro",
                duration=2.5,
                data=TimelineEventData(
                    left=left,
                    right=right,
                    left_hp_before=left_hp,
                    right_hp_before=right_hp,
                    left_hp_after=left_hp,
                    right_hp_after=right_hp,
                ),
            )
        )

        for event in result.events:
            # Считаем новые HP ДО создания события
            left_hp_after = left_hp
            right_hp_after = right_hp

            attacker_left = event.attacker.name == left.name

            if attacker_left:
                right_hp_after = max(
                    0, min(right.max_hp, right_hp + event.hp_delta_defender)
                )
                if event.type == "regen":
                    left_hp_after = max(
                        0, min(left.max_hp, left_hp + event.hp_delta_attacker)
                    )
            else:
                left_hp_after = max(
                    0, min(left.max_hp, left_hp + event.hp_delta_defender)
                )
                if event.type == "regen":
                    right_hp_after = max(
                        0, min(right.max_hp, right_hp + event.hp_delta_attacker)
                    )

            # Пауза — показываем HP до события
            events.append(
                TimelineEvent(
                    type="pause",
                    duration=0.8,
                    data=TimelineEventData(
                        left=left,
                        right=right,
                        left_hp_before=left_hp,
                        right_hp_before=right_hp,
                        left_hp_after=left_hp,
                        right_hp_after=right_hp,
                        attacker_left=attacker_left,
                    ),
                )
            )

            # Боевое событие — HP плавно меняется от before к after
            events.append(
                TimelineEvent(
                    type=event.type,
                    duration=None,
                    data=TimelineEventData(
                        left=left,
                        right=right,
                        left_hp_before=left_hp,
                        right_hp_before=right_hp,
                        left_hp_after=left_hp_after,
                        right_hp_after=right_hp_after,
                        attacker_left=attacker_left,
                        battle_event=event,
                    ),
                )
            )

            left_hp = left_hp_after
            right_hp = right_hp_after

        events.append(
            TimelineEvent(
                type="outro",
                duration=3.0,
                data=TimelineEventData(
                    left=left,
                    right=right,
                    left_hp_before=left_hp,
                    right_hp_before=right_hp,
                    left_hp_after=left_hp,
                    right_hp_after=right_hp,
                    winner=result.winner,
                    is_draw=result.is_draw,
                ),
            )
        )

        return events
