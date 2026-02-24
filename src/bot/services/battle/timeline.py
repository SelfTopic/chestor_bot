from typing import List

from src.bot.services.battle.mechanics import BattleResult
from src.bot.services.battle.models import (
    BattleFighter,
    TimelineEvent,
    TimelineEventData,
)

# timeline.py


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

        left_hp_before = left_hp
        right_hp_before = right_hp

        # Интро
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
            # Пауза перед действием
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
                    ),
                )
            )

            # Определяем сторону
            attacker_left = event.attacker.name == left.name

            # Боевое событие
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
                    ),
                )
            )

            # Обновляем HP
            if event.attacker.name == left.name:
                # атакует левый
                right_hp_after = event.defender_hp_after
                left_hp_after = left_hp
                if event.type == "regen":
                    left_hp_after = event.attacker_hp_after
            else:
                # атакует правый
                left_hp_after = event.defender_hp_after
                right_hp_after = right_hp
                if event.type == "regen":
                    right_hp_after = event.attacker_hp_after

            # сохраняем финальные
            left_hp = left_hp_after
            right_hp = right_hp_after

            events[-1].data.left_hp_after = left_hp_after
            events[-1].data.right_hp_after = right_hp_after

        # Аутро
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
