"""Дебаг-превью "бить моба" - ЧИСТАЯ симуляция без побочных эффектов: не
пишет ничего в БД (HP гуля не трогается, победа/поражение не считается,
наград и кулдауна нет). Существует, чтобы на реальных статах реального
гуля вживую увидеть шансы против моба (движок стохастический - жать можно
сколько угодно раз, исход каждый раз разный) и проверить, что
build_rich_message реально доходит до Telegram и нормально выглядит в
живом чате.

Настоящий роутер боя с мобом (кулдаун, награды, персистентность
урона/смерти) - отдельная, ещё не написанная задача, см. BATTLE_DESIGN.md
и BATTLE_ENGINE.md 1.1."""

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...exceptions import (
    FighterIsDeadError,
    FighterNotCombatReadyError,
    GhoulNotFoundInDatabase,
)
from ...services import (
    BattleService,
    BattleTextGenerator,
    DialogService,
    GhoulService,
    UserService,
)

router = Router(name=__name__)

logger = logging.getLogger(__name__)


@router.message(F.text.lower() == "бить моба")
@inject
async def mob_fight_preview_handler(
    message: Message,
    user_service: UserService = Provide[Container.user_service],
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    battle_service: BattleService = Provide[Container.battle_service],
    battle_text_generator: BattleTextGenerator = Provide[Container.battle_text_generator],
    dialog_service: DialogService = Provide[Container.dialog_service],
) -> None:
    if not message.from_user:
        logger.warning("User not found in message")
        return None

    user = await user_service.get(find_by=message.from_user.id)
    if not user:
        raise ValueError("User not found in database")

    ghoul = await ghoul_service.get(message)
    if not ghoul:
        raise GhoulNotFoundInDatabase("Ghoul not found for user")

    # has_pending_confirmation не передаём - для боя с мобом нечего
    # проверять (моб не участвует в очереди дуэлей), и хранилища pending-
    # вызовов пока всё равно нет (см. BattleService.validate_ghoul).
    try:
        battle_service.validate_ghoul(ghoul)
    except FighterIsDeadError:
        await message.reply(text=dialog_service.text(key="dead_ghoul_reply"))
        return None
    except FighterNotCombatReadyError as exc:
        await message.reply(
            text=dialog_service.text(
                key="not_combat_ready", health=exc.health, threshold=exc.threshold
            )
        )
        return None

    player = battle_service.ghoul_to_fighter(ghoul, user.full_name, ghoul_service)
    result, mob = battle_service.run_against_mob(player)

    rank_a = ghoul_service.get_danger_rank(battle_service.power_of(player.snapshot))
    rank_b = ghoul_service.get_danger_rank(battle_service.power_of(mob.snapshot))

    rich_message = battle_text_generator.build_rich_message(
        result, player, mob, rank_a, rank_b
    )
    try:
        await message.answer_rich(rich_message=rich_message)
    except TelegramAPIError:
        logger.warning(
            "send_rich_message failed for mob fight preview, falling back to plain text",
            exc_info=True,
        )
        fallback_text = battle_text_generator.build_plain_text(
            result, player, mob, rank_a, rank_b
        )
        await message.answer(text=fallback_text)

    return None


__all__ = ["router"]
