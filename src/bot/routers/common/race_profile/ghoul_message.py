from dataclasses import dataclass
from typing import Any

from selfrot.types import (
    InputRichBlockDetails,
    InputRichBlockDivider,
    InputRichBlockList,
    InputRichBlockListItem,
    InputRichBlockSectionHeading,
    InputRichMessage,
)

from src.bot.game_configs import STATS
from src.bot.services import GhoulService
from src.bot.services.dialog import DialogService
from src.bot.utils import calculate_kagune, get_hunger_tier, level_progress_bar
from src.database.models import Ghoul, User

from ...rich import paragraph


@dataclass(frozen=True)
class BattleStats:
    """Бои гуля: с игроками (дуэли) и с мобами отдельно, «всего» включает оба вида."""

    wins: int
    losses: int
    total: int
    mob_wins: int
    mob_losses: int
    mob_total: int


def rich_profile(
    user: User,
    ghoul: Ghoul,
    ghoul_service: GhoulService,
    danger_rank: str,
    power: int,
    stats: BattleStats,
) -> InputRichMessage:
    """Профиль гуля как rich-сообщение (Bot API 10.1+), см. BATTLE_DESIGN.md
    ("UX профиля"). "Всего боёв" включает дуэли и мобов, вторая строка честно
    показывает только мобов."""

    tier = get_hunger_tier(ghoul.hunger)

    kagune_items = [
        InputRichBlockListItem(
            blocks=[
                paragraph(
                    f"{kagune_type.value['name']} - "
                    f"{ghoul_service.get_kagune_strength(ghoul, kagune_type)}"
                )
            ]
        )
        for kagune_type in ghoul_service.owned_kagune_types(ghoul)
    ]

    stat_items = [
        InputRichBlockListItem(blocks=[paragraph(f"{label}: {getattr(ghoul, key)}")])
        for label, key, _emoji in STATS
        if key != "max_health"  # здоровье показываем отдельной строкой ниже
    ]

    blocks: list[Any] = [
        InputRichBlockSectionHeading(
            text=f"👤 Профиль гуля {danger_rank} ранга {user.full_name}", size=3
        ),
        paragraph(f"📈 Уровень: {ghoul.level}"),
        paragraph(
            f"{level_progress_bar(ghoul.level_progress)} {round(ghoul.level_progress)}%"
        ),
        paragraph(f"🍖 Голод: {ghoul.hunger}% ({tier.name})"),
        paragraph(f"♦️ RC-клеток: {ghoul.rc_money}"),
        InputRichBlockDetails(
            summary="👁‍🗨 Типы кагуне - сила",
            blocks=[InputRichBlockList(items=kagune_items)],
        ),
        paragraph(f"👌 Сломано пальцев: {ghoul.snap_count}"),
        paragraph(f"☕️ Выпито кофе: {ghoul.coffee_count}"),
        paragraph(f"🥩 Съедено людей: {ghoul.eat_humans}"),
        InputRichBlockDetails(
            summary="Статы",
            blocks=[
                InputRichBlockList(items=stat_items),
                paragraph(f"❤️ Здоровье: {ghoul.health}/{ghoul.max_health}"),
                paragraph(f"⚡ Боевая мощь: {power}"),
            ],
        ),
        paragraph(f"🥩 Съедено гулей: {ghoul.eat_ghouls}"),
        paragraph(
            f"⚔️ Всего боёв: {stats.total} ({stats.wins} побед / {stats.losses} поражений)"
        ),
        paragraph(
            f"👹 Боёв с мобами: {stats.mob_total} ({stats.mob_wins} побед / {stats.mob_losses} поражений)"
        ),
        InputRichBlockDivider(),
        paragraph(f"🧬 Какуджа: {'Есть' if ghoul.is_kakuja else 'Нет'}"),
        paragraph(f"☠️ Смертей: {ghoul.deaths}"),
    ]

    return InputRichMessage(blocks=blocks)


def plain_profile(
    dialog_service: DialogService,
    user: User,
    ghoul: Ghoul,
    ghoul_service: GhoulService,
    danger_rank: str,
    power: int,
    stats: BattleStats,
) -> str:
    """Тот же профиль обычным текстом: на случай, когда rich-сообщение не принято."""
    return dialog_service.text(
        key="ghoul_profile",
        name=user.full_name,
        strength=ghoul.strength,
        snap_count=ghoul.snap_count,
        kagune_type=calculate_kagune(ghoul.kagune_type_bit)[0].value["name"],
        health=ghoul.health,
        max_health=ghoul.max_health,
        coffee_count=ghoul.coffee_count,
        strength_kagune=ghoul_service.total_kagune_strength(ghoul),
        rc_count=ghoul.rc_money,
        regeneration=ghoul.regeneration,
        eat_ghouls=ghoul.eat_ghouls,
        eat_humans=ghoul.eat_humans,
        dexterity=ghoul.dexterity,
        speed=ghoul.speed,
        is_kakuja="Есть" if ghoul.is_kakuja else "Нет",
        level=ghoul.level,
        power=power,
        danger_rank=danger_rank,
        wins=stats.wins,
        losses=stats.losses,
        total_battles=stats.total,
        mob_wins=stats.mob_wins,
        mob_losses=stats.mob_losses,
        mob_battles=stats.mob_total,
    )
