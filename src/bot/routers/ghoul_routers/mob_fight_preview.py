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
from typing import Dict, List, Optional, Protocol

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...exceptions import GhoulNotFoundInDatabase
from ...services import (
    BattleTextGenerator,
    DialogService,
    GhoulService,
    MobService,
    UserService,
)
from ...services.battle_engine.core import Battle, Fighter, FighterSnapshot
from ...types import KaguneType
from src.database.models import Ghoul

router = Router(name=__name__)

logger = logging.getLogger(__name__)


class _KaguneLookup(Protocol):
    """Только то подмножество GhoulService, которое реально нужно
    _snapshot_from_ghoul - структурный тип (Protocol), а не конкретный
    класс, чтобы тесты могли подставить лёгкий дублёр без БД (см.
    tests/unit/mob_fight_preview_test.py и тот же паттерн в
    race_profile_rich_message_test.py)."""

    def owned_kagune_types(self, ghoul: Ghoul) -> List[KaguneType]: ...
    def get_kagune_strength(self, ghoul: Ghoul, kagune_type: KaguneType) -> Optional[int]: ...


def _snapshot_from_ghoul(ghoul: Ghoul, name: str, ghoul_service: _KaguneLookup) -> FighterSnapshot:
    kagune_strength: Dict[KaguneType, int] = {}
    for kagune_type in ghoul_service.owned_kagune_types(ghoul):
        strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
        # owned_kagune_types уже отфильтровал типы с None (см. GhoulService) -
        # assert только чтобы pyright не видел здесь Optional[int].
        assert strength is not None
        kagune_strength[kagune_type] = strength

    return FighterSnapshot(
        id=ghoul.id,
        name=name,
        strength=ghoul.strength,
        dexterity=ghoul.dexterity,
        regeneration=ghoul.regeneration,
        speed=ghoul.speed,
        health=ghoul.max_health,  # полный боевой пул на старт боя, не текущее (возможно урезанное) HP
        hunger=ghoul.hunger,
        is_kakuja=ghoul.is_kakuja,
        kagune_strength=kagune_strength,
    )


def _snapshot_power(snapshot: FighterSnapshot) -> int:
    """То же слагаемое, что GhoulService.calculate_power, но по
    FighterSnapshot - у моба нет строки Ghoul в БД, считать не от кого
    другого."""

    return (
        snapshot.strength
        + snapshot.dexterity
        + snapshot.speed
        + snapshot.health
        + snapshot.regeneration
        + snapshot.total_kagune_strength
    )


@router.message(F.text.lower() == "бить моба")
@inject
async def mob_fight_preview_handler(
    message: Message,
    user_service: UserService = Provide[Container.user_service],
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    mob_service: MobService = Provide[Container.mob_service],
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

    if ghoul.is_dead:
        await message.reply(text=dialog_service.text(key="dead_ghoul_reply"))
        return None

    player_snapshot = _snapshot_from_ghoul(ghoul, user.full_name, ghoul_service)
    mob_snapshot = mob_service.generate_mob(player_snapshot)

    fighter_a = Fighter(player_snapshot)
    fighter_b = Fighter(mob_snapshot)
    result = Battle(fighter_a, fighter_b).run()

    rank_a = ghoul_service.get_danger_rank(ghoul_service.calculate_power(ghoul))
    rank_b = ghoul_service.get_danger_rank(_snapshot_power(mob_snapshot))

    rich_message = battle_text_generator.build_rich_message(
        result, fighter_a, fighter_b, rank_a, rank_b
    )
    try:
        await message.answer_rich(rich_message=rich_message)
    except TelegramAPIError:
        logger.warning(
            "send_rich_message failed for mob fight preview, falling back to plain text",
            exc_info=True,
        )
        fallback_text = battle_text_generator.build_plain_text(
            result, fighter_a, fighter_b, rank_a, rank_b
        )
        await message.answer(text=fallback_text)

    return None


__all__ = ["router"]
