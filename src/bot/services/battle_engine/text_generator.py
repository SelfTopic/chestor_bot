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

from typing import List

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
        blocks: List[InputRichBlockUnion] = [
            InputRichBlockSectionHeading(
                text=f"⚔️ {fighter_a.name} vs {fighter_b.name}", size=3
            ),
            InputRichBlockParagraph(text=self._winner_line(result, fighter_a, fighter_b)),
            InputRichBlockParagraph(
                text=(
                    f"❤️ Финальное HP: {fighter_a.name} — {round(result.final_hp_a)}, "
                    f"{fighter_b.name} — {round(result.final_hp_b)}"
                )
            ),
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
        rich-сообщении, тут - голая сводка."""

        return self._dialog_service.text(
            key="battle_result_summary",
            name_a=fighter_a.name,
            name_b=fighter_b.name,
            winner_line=self._winner_line(result, fighter_a, fighter_b),
            final_hp_a=round(result.final_hp_a),
            final_hp_b=round(result.final_hp_b),
            rounds=len(result.rounds),
        )

    def _winner_line(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> str:
        if result.winner is None:
            return "🤝 Ничья."
        winner, loser = (
            (fighter_a, fighter_b) if result.winner == "a" else (fighter_b, fighter_a)
        )
        outcome = "повержен" if result.ended_naturally else "проиграл по итогам раундов"
        return f"🏆 Победитель: {winner.name}. {loser.name} {outcome}."

    def _round_lines(
        self, result: BattleResult, fighter_a: Fighter, fighter_b: Fighter
    ) -> List[str]:
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

            actions_a = " ".join(_format_action(a) for a in round_result.actions_a) or "—"
            actions_b = " ".join(_format_action(a) for a in round_result.actions_b) or "—"
            lines.append(
                f"Раунд {round_result.round_number}: "
                f"{fighter_a.name} {actions_a} ({round(display_hp_a)} HP) — "
                f"{fighter_b.name} {actions_b} ({round(display_hp_b)} HP)"
            )

        return lines

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


__all__ = ["BattleTextGenerator"]
