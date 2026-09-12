"""Команда "боевая мощь" (BATTLE_ENGINE.md 8.4) - две таблицы рядом:
"фиктивная" (вакуумные/паспортные статы, те же числа, что суммирует
`GhoulService.calculate_power`) и "боевая" (реальный боевой путь стата -
значение → влияние голода → влияние кагуне, где правый столбец - то, что
РЕАЛЬНО участвует в бою прямо сейчас, см. `EffectiveStats`). Подробности
про сами множители голода/кагуне не дублируются здесь - под таблицами
ссылки на "голод" и "кагуне".

Здоровье - особый случай: "фиктивная" колонка берёт `ghoul.max_health`
("паспортный" потолок, та же величина, что суммирует calculate_power),
а базовое значение в "боевой" таблице - реальное ТЕКУЩЕЕ `ghoul.health`
(то, с чем боец реально входит в бой, см. `BattleService.ghoul_to_fighter`)
- разница между ними и есть самое наглядное "сколько ты реально можешь
прямо сейчас"."""

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    InputRichBlockDivider,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichBlockUnion,
    InputRichMessage,
    Message,
    RichBlockTableCell,
)
from dependency_injector.wiring import Provide, inject

from src.database.models import Ghoul

from ...containers import Container
from ...services import BattleService, DialogService, GhoulService, UserService
from ...services.battle_engine.core import StatBreakdown, compute_stat_breakdown
from ...utils import get_hunger_tier

logger = logging.getLogger(__name__)

router = Router(name=__name__)

# Порядок и подписи статов, участвующих в обеих таблицах - тот же порядок,
# что STATS в game_configs.py (без max_health отдельной строкой - здесь он
# и есть "Здоровье").
_STAT_LABELS: list[tuple[str, str]] = [
    ("strength", "Сила"),
    ("dexterity", "Ловкость"),
    ("speed", "Скорость"),
    ("health", "Здоровье"),
    ("regeneration", "Регенерация"),
]


def _paragraph(text: str) -> InputRichBlockParagraph:
    return InputRichBlockParagraph(text=text)


def _cell(text: str, *, header: bool = False) -> RichBlockTableCell:
    return RichBlockTableCell(
        align="center", valign="middle", text=text, is_header=header or None
    )


def _fmt(value: float) -> str:
    return str(round(value, 1))


def build_combat_power_rich_message(
    user,
    ghoul: Ghoul,
    danger_rank: str,
    ghoul_service: GhoulService,
    battle_service: BattleService,
) -> InputRichMessage:
    fighter = battle_service.ghoul_to_fighter(ghoul, user.full_name, ghoul_service)
    breakdown: dict[str, StatBreakdown] = compute_stat_breakdown(fighter.snapshot)

    vacuum_kagune = ghoul_service.total_kagune_strength(ghoul)
    vacuum_power = ghoul_service.calculate_power(ghoul)
    combat_base_power = battle_service.power_of(fighter.snapshot)
    effective_power = battle_service.effective_power_of(fighter.stats)

    # "Фиктивная" (вакуумная/паспортная) таблица - только базовые значения,
    # здоровье - max_health (та же величина, что и calculate_power).
    vacuum_values = {
        "strength": ghoul.strength,
        "dexterity": ghoul.dexterity,
        "speed": ghoul.speed,
        "health": ghoul.max_health,
        "regeneration": ghoul.regeneration,
    }
    vacuum_rows = [
        [_cell(label), _cell(str(vacuum_values[key]))] for key, label in _STAT_LABELS
    ]
    vacuum_rows.append([_cell("Кагуне"), _cell(str(vacuum_kagune))])
    vacuum_rows.append([_cell("Итого"), _cell(str(vacuum_power))])

    vacuum_table = InputRichBlockTable(
        cells=[[_cell("Стат", header=True), _cell("Значение", header=True)], *vacuum_rows],
        is_bordered=True,
        is_striped=True,
    )

    # "Боевая" таблица - значение → влияние голода → влияние кагуне (правый
    # столбец = реальное боевое значение прямо сейчас, EffectiveStats).
    combat_rows = [
        [
            _cell(label),
            _cell(_fmt(breakdown[key].base)),
            _cell(_fmt(breakdown[key].after_hunger)),
            _cell(_fmt(breakdown[key].after_kagune)),
        ]
        for key, label in _STAT_LABELS
    ]

    # Сила кагуне не идёт через типовой множитель (см. compute_effective_stats) -
    # "влияние голода" и "влияние кагуне" совпадают, если гуль не какудж.
    tier = get_hunger_tier(ghoul.hunger)
    kagune_after_hunger = vacuum_kagune * tier.rising_multiplier
    combat_rows.append(
        [
            _cell("Кагуне"),
            _cell(str(vacuum_kagune)),
            _cell(_fmt(kagune_after_hunger)),
            _cell(_fmt(fighter.stats.kagune_strength)),
        ]
    )

    combat_total_after_hunger = (
        sum(breakdown[key].after_hunger for key, _ in _STAT_LABELS) + kagune_after_hunger
    )
    combat_rows.append(
        [
            _cell("Итого"),
            _cell(str(round(combat_base_power))),
            _cell(_fmt(combat_total_after_hunger)),
            _cell(_fmt(effective_power)),
        ]
    )

    combat_table = InputRichBlockTable(
        cells=[
            [
                _cell("Стат", header=True),
                _cell("Значение", header=True),
                _cell("Влияние голода", header=True),
                _cell("Влияние кагуне", header=True),
            ],
            *combat_rows,
        ],
        is_bordered=True,
        is_striped=True,
    )

    blocks: list[InputRichBlockUnion] = [
        InputRichBlockSectionHeading(
            text=f"⚡ Боевая мощь гуля {danger_rank} ранга {user.full_name}", size=3
        ),
        vacuum_table,
        InputRichBlockDivider(),
        _paragraph(
            "Самое правое значение в таблице ниже - значение, которое реально "
            "будет использоваться в бою."
        ),
        combat_table,
        InputRichBlockDivider(),
        _paragraph('Если надо узнать, как голод влияет на статистики - напиши "голод".'),
        _paragraph("Если надо узнать, как кагуне влияет на статистики - используй /kagune."),
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

    vacuum_power = ghoul_service.calculate_power(ghoul)
    danger_rank = ghoul_service.get_danger_rank(vacuum_power)

    try:
        rich_message = build_combat_power_rich_message(
            user, ghoul, danger_rank, ghoul_service, battle_service
        )
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
            danger_rank=danger_rank,
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
            vacuum_power=vacuum_power,
            effective_power=round(battle_service.effective_power_of(stats), 1),
        )
        return await message.answer(text=fallback_text)


@router.message(F.text.lower() == "бм")
@inject
async def combat_power_short_handler(
    message: Message,
    user_service: UserService = Provide[Container.user_service],
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    battle_service: BattleService = Provide[Container.battle_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
) -> Message:
    """Короткий алиас "боевой мощи" (пожелание игроков по UX после
    тестирования) - без похода в rich-таблицы, просто два числа: вакуумная
    мощь (вне боя) и эффективная (в бою прямо сейчас)."""

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

    vacuum_power = ghoul_service.calculate_power(ghoul)
    fighter = battle_service.ghoul_to_fighter(ghoul, user.full_name, ghoul_service)
    effective_power = battle_service.effective_power_of(fighter.stats)

    return await message.answer(
        text=dialog_service.text(
            key="combat_power_short",
            vacuum_power=vacuum_power,
            effective_power=round(effective_power, 1),
        )
    )


__all__ = ["router"]
