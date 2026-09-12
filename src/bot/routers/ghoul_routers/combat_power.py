"""Команда "боевая мощь" (BATTLE_ENGINE.md 8.4) - показывает и вакуумные
(косметика, "паспортные", те же числа, что суммирует `GhoulService.
calculate_power` для наград/сравнения силы, см. 4.2), и эффективные
(боевые ПРЯМО СЕЙЧАС - после цепочки модификаторов голод → тип кагуне →
какудж) значения статов рядом друг с другом. Цель - чтобы игрок в любой
момент мог честно оценить свою боеспособность, а не только "номинальную"
силу из `распрофиль`.

Здоровье - особый случай: вакуумная колонка берёт `ghoul.max_health`
("паспортный" потолок, та же величина, что суммирует calculate_power),
эффективная - реальный боевой пул ПРЯМО СЕЙЧАС (строится от текущего
`ghoul.health`, см. `BattleService.ghoul_to_fighter`) - разница между
ними и есть самое наглядное "сколько ты реально можешь прямо сейчас"."""

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    InputRichBlockDivider,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockUnion,
    InputRichMessage,
    Message,
)
from dependency_injector.wiring import Provide, inject

from src.database.models import Ghoul

from ...containers import Container
from ...services import BattleService, DialogService, GhoulService, UserService

logger = logging.getLogger(__name__)

router = Router(name=__name__)


def _paragraph(text: str) -> InputRichBlockParagraph:
    return InputRichBlockParagraph(text=text)


def build_combat_power_rich_message(
    user, ghoul: Ghoul, ghoul_service: GhoulService, battle_service: BattleService
) -> InputRichMessage:
    fighter = battle_service.ghoul_to_fighter(ghoul, user.full_name, ghoul_service)
    stats = fighter.stats

    vacuum_kagune = ghoul_service.total_kagune_strength(ghoul)
    vacuum_power = ghoul_service.calculate_power(ghoul)
    effective_power = battle_service.effective_power_of(stats)

    blocks: list[InputRichBlockUnion] = [
        InputRichBlockSectionHeading(text=f"⚡ Боевая мощь {user.full_name}", size=3),
        _paragraph(f"🤟 Сила: {ghoul.strength} → {round(stats.strength, 1)}"),
        _paragraph(f"🤾‍♀️ Ловкость: {ghoul.dexterity} → {round(stats.dexterity, 1)}"),
        _paragraph(f"🏃 Скорость: {ghoul.speed} → {round(stats.speed, 1)}"),
        _paragraph(f"❤️ Здоровье: {ghoul.max_health} → {round(stats.health, 1)}"),
        _paragraph(f"❣️ Регенерация: {ghoul.regeneration} → {round(stats.regeneration, 1)}"),
        _paragraph(f"♦️ Кагуне: {vacuum_kagune} → {round(stats.kagune_strength, 1)}"),
        InputRichBlockDivider(),
        _paragraph(f"📊 Итого: {vacuum_power} → {round(effective_power, 1)}"),
    ]

    return InputRichMessage(blocks=blocks)


@router.message(F.text.lower() == "боевая мощь")
@inject
async def combat_power_handler(
    message: Message,
    user_service: UserService = Provide[Container.user_service],
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    battle_service: BattleService = Provide[Container.battle_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
) -> Message:
    if not message.from_user:
        logger.error("User not found in message")
        raise ValueError("User not found in message")

    user = await user_service.get(message.from_user.id)
    if not user:
        logger.error("User not found in database")
        raise ValueError("User not found in database")

    ghoul = await ghoul_service.get(message)
    if not ghoul:
        logger.error(f"Ghoul not found for {message.from_user.id} despite GhoulMiddleware")
        raise ValueError("Ghoul not found")

    if ghoul.is_dead:
        return await message.answer(
            text=dialog_service.text(key="dead_ghoul_profile", name=user.full_name)
        )

    rich_message = build_combat_power_rich_message(user, ghoul, ghoul_service, battle_service)

    try:
        return await message.answer_rich(rich_message=rich_message)
    except TelegramAPIError:
        logger.warning(
            "send_rich_message failed for combat power, falling back to plain text",
            exc_info=True,
        )
        fighter = battle_service.ghoul_to_fighter(ghoul, user.full_name, ghoul_service)
        stats = fighter.stats
        fallback_text = dialog_service.text(
            key="combat_power",
            name=user.full_name,
            vacuum_strength=ghoul.strength,
            effective_strength=round(stats.strength, 1),
            vacuum_dexterity=ghoul.dexterity,
            effective_dexterity=round(stats.dexterity, 1),
            vacuum_speed=ghoul.speed,
            effective_speed=round(stats.speed, 1),
            vacuum_health=ghoul.max_health,
            effective_health=round(stats.health, 1),
            vacuum_regeneration=ghoul.regeneration,
            effective_regeneration=round(stats.regeneration, 1),
            vacuum_kagune=ghoul_service.total_kagune_strength(ghoul),
            effective_kagune=round(stats.kagune_strength, 1),
            vacuum_power=ghoul_service.calculate_power(ghoul),
            effective_power=round(battle_service.effective_power_of(stats), 1),
        )
        return await message.answer(text=fallback_text)


__all__ = ["router"]
