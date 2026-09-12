import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import (
    InputRichBlockDetails,
    InputRichBlockDivider,
    InputRichBlockList,
    InputRichBlockListItem,
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
from ...game_configs import STATS
from ...services import BattleRecordService, DialogService, GhoulService, UserService
from ...services.battle_engine.core import KAGUNE_TYPE_MULTIPLIERS, KAGUNE_TYPE_PRIORITY_STAT
from ...types import KaguneType, Race
from ...utils import calculate_kagune, get_hunger_tier, level_progress_bar

logger = logging.getLogger(__name__)

router = Router(name=__name__)


def _paragraph(text: str) -> InputRichBlockParagraph:
    return InputRichBlockParagraph(text=text)


def _table_cell(text: str, *, header: bool = False) -> RichBlockTableCell:
    return RichBlockTableCell(
        align="center", valign="middle", text=text, is_header=header or None
    )


# Порядок и подписи статов в таблице влияния кагуне - тот же порядок, что
# используется в "боевая мощь" (combat_power.py), для единообразия UI.
_KAGUNE_STAT_LABELS: list[tuple[str, str]] = [
    ("strength", "Сила"),
    ("dexterity", "Ловкость"),
    ("speed", "Скорость"),
    ("health", "Здоровье"),
    ("regeneration", "Регенерация"),
]


def build_kagune_info_rich_message() -> InputRichMessage:
    """Справочная таблица "какой тип кагуне на какой стат и с каким
    множителем влияет" (BATTLE_DESIGN.md "Множители типов кагуне") - не
    привязана к конкретному гулю (нет входных параметров), поэтому команда
    доступна всем без похода в профиль - см. `race_profile_router` вместо
    отдельного роутера, чтобы не плодить модуль ради одного хендлера."""

    header_row = [_table_cell("Тип", header=True)] + [
        _table_cell(label, header=True) for _, label in _KAGUNE_STAT_LABELS
    ]

    rows = [header_row]
    for kagune_type in KaguneType:
        multipliers = KAGUNE_TYPE_MULTIPLIERS.get(kagune_type, {})
        row = [_table_cell(str(kagune_type.value["name"]))]
        for stat_key, _ in _KAGUNE_STAT_LABELS:
            if stat_key not in multipliers:
                row.append(_table_cell("—"))
                continue
            mark = "★" if KAGUNE_TYPE_PRIORITY_STAT[kagune_type] == stat_key else ""
            row.append(_table_cell(f"×{multipliers[stat_key]}{mark}"))
        rows.append(row)

    table = InputRichBlockTable(cells=rows, is_bordered=True, is_striped=True)

    general_info = InputRichBlockDetails(
        summary="📖 Общая информация о кагуне",
        blocks=[
            _paragraph(
                "Какухо - орган в теле гуля, управляющий RC-клетками: "
                "регенерация, усиление тела и кагуне вне тела. Его "
                "расположение определяет боевой стиль каждого типа."
            ),
            _paragraph(
                "🔸 Укаку (плечи): приток RC в мозг и руки - высокая "
                "скорость, частые лёгкие удары. Минус - низкая выносливость, "
                "однообразие легко пережидается."
            ),
            _paragraph(
                "🔸 Коукаку (лопатки): RC усиливает мышцы спины и рук - "
                "мощный физический удар. Минус - низкая скорость, ловкий "
                "противник уворачивается и контратакует."
            ),
            _paragraph(
                "🔸 Ринкаку (поясница): RC равномерно расходится по телу - "
                "высокая выносливость и регенерация. Явных слабостей почти "
                "нет."
            ),
            _paragraph(
                "🔸 Бикаку (копчик): RC концентрируется в корпусе и ногах - "
                "понемногу всех усилений сразу, универсал без выраженного "
                "минуса."
            ),
            _paragraph(
                "Как это влияет на урон: каждый удар решается монеткой "
                "«физический / кагуне» - первый удар боя всегда физический, "
                "дальше шанс физического падает на 10 п.п. за каждый "
                "нанесённый физический удар (бой постепенно скатывается в "
                "удары кагуне). Урон кагуне обычно выше - считается от силы "
                "И силы кагуне вместе, физический - только от силы."
            ),
            _paragraph(
                "Защита: если кагуне поднято - блокирует 45-75% физической "
                "атаки, а против чужого удара кагуне - 10-20% (если своя "
                "сила кагуне не меньше чужой) либо 0%. Без поднятого кагуне "
                "- голое тело блокирует физику на 10-20% (если здоровье не "
                "меньше, чем у атакующего) и вообще не блокирует удары "
                "кагуне. Шанс успеть поднять кагуне под конкретный удар "
                "зависит от ловкости и скорости - при равных статах 50/50."
            ),
        ],
    )

    blocks: list[InputRichBlockUnion] = [
        general_info,
        InputRichBlockSectionHeading(text="♦️ Влияние типов кагуне на статы", size=3),
        table,
        _paragraph(
            "★ - приоритетный стат типа: если открыто несколько типов, "
            "трогающих один стат, побеждает «хозяин» (★), иначе берётся "
            "наименьший из множителей (правило стаков, см. BATTLE_DESIGN.md)."
        ),
        _paragraph(
            "Сила кагуне (сумма силы всех открытых типов) сама по себе НЕ "
            "множится типом кагуне - только голодом (растущий стат) и "
            "какуджей."
        ),
    ]

    return InputRichMessage(blocks=blocks)


@router.message(F.text.lower() == "кагуне")
@router.message(Command("kagune"))
@inject
async def kagune_info_handler(
    message: Message,
    dialog_service: DialogService = Provide[Container.dialog_service],
) -> Message:
    try:
        return await message.answer_rich(rich_message=build_kagune_info_rich_message())
    except TelegramAPIError:
        logger.warning(
            "send_rich_message failed for kagune info, falling back to plain text",
            exc_info=True,
        )
        return await message.answer(text=dialog_service.text(key="kagune_info"))


def build_ghoul_profile_rich_message(
    user,
    ghoul: Ghoul,
    ghoul_service: GhoulService,
    danger_rank: str,
    power: int,
    wins: int,
    losses: int,
    total_battles: int,
    mob_wins: int,
    mob_losses: int,
    mob_battles: int,
) -> InputRichMessage:
    """Собирает профиль гуля как rich-сообщение (Bot API 10.1+, aiogram
    3.29+), см. BATTLE_DESIGN.md ("UX профиля"). Блоки собираются из
    типизированных InputRichBlock*, а не из markdown-строки - синтаксис
    markdown-диалекта для sendRichMessage нигде в исходниках aiogram не
    задокументирован (только сами типы), рисковать его угадать не стали.

    "Всего боёв" из мокапа - теперь реализовано (BATTLE_ENGINE.md 5.2),
    источник - BattleRecordService.count_wins/count_losses/count_total_battles
    (таблица `battles`, всё время, не дневное окно). Отдельная строка под
    бои с мобами (count_*_vs_mobs) - НЕ смешивать с дуэлями в одном числе
    (см. чат) - "Всего боёв" включает оба типа разом, вторая строка честно
    показывает только мобов."""

    tier = get_hunger_tier(ghoul.hunger)

    kagune_items = [
        InputRichBlockListItem(
            blocks=[
                _paragraph(
                    f"{kagune_type.value['name']} - "
                    f"{ghoul_service.get_kagune_strength(ghoul, kagune_type)}"
                )
            ]
        )
        for kagune_type in ghoul_service.owned_kagune_types(ghoul)
    ]

    stat_items = [
        InputRichBlockListItem(blocks=[_paragraph(f"{label}: {getattr(ghoul, key)}")])
        for label, key, _emoji in STATS
        if key != "max_health"  # здоровье показываем отдельной строкой ниже
    ]

    blocks: list[InputRichBlockUnion] = [
        InputRichBlockSectionHeading(
            text=f"👤 Профиль гуля {danger_rank} ранга {user.full_name}", size=3
        ),
        _paragraph(f"📈 Уровень: {ghoul.level}"),
        _paragraph(
            f"{level_progress_bar(ghoul.level_progress)} {round(ghoul.level_progress)}%"
        ),
        _paragraph(f"🍖 Голод: {ghoul.hunger}% ({tier.name})"),
        _paragraph(f"♦️ RC-клеток: {ghoul.rc_money}"),
        InputRichBlockDetails(
            summary="👁‍🗨 Типы кагуне - сила",
            blocks=[InputRichBlockList(items=kagune_items)],
        ),
        _paragraph(f"👌 Сломано пальцев: {ghoul.snap_count}"),
        _paragraph(f"☕️ Выпито кофе: {ghoul.coffee_count}"),
        _paragraph(f"🥩 Съедено людей: {ghoul.eat_humans}"),
        InputRichBlockDetails(
            summary="Статы",
            blocks=[
                InputRichBlockList(items=stat_items),
                _paragraph(f"❤️ Здоровье: {ghoul.health}/{ghoul.max_health}"),
                _paragraph(f"⚡ Боевая мощь: {power}"),
            ],
        ),
        _paragraph(f"🥩 Съедено гулей: {ghoul.eat_ghouls}"),
        _paragraph(
            f"⚔️ Всего боёв: {total_battles} ({wins} побед / {losses} поражений)"
        ),
        _paragraph(
            f"👹 Боёв с мобами: {mob_battles} ({mob_wins} побед / {mob_losses} поражений)"
        ),
        InputRichBlockDivider(),
        _paragraph(f"🧬 Какуджа: {'Есть' if ghoul.is_kakuja else 'Нет'}"),
        _paragraph(f"☠️ Смертей: {ghoul.deaths}"),
    ]

    return InputRichMessage(blocks=blocks)


@router.message(F.text.lower() == "распрофиль")
@router.message(Command("race_profile"))
@inject
async def profile_handler(
    message: Message,
    user_service: UserService = Provide[Container.user_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    battle_record_service: BattleRecordService = Provide[
        Container.battle_record_service
    ],
) -> Message:
    if not message.from_user:
        logger.error("User not found in message.")
        raise ValueError("User not found in message")

    user = await user_service.get(message.from_user.id)

    if not user:
        logger.error("User not found in database.")
        raise ValueError("User not found in database")

    race = user_service.race(user.race_bit)

    if not race:
        raise

    profile = None

    if race == Race.GHOUL:
        profile = await ghoul_service.get(message)

    else:
        profile = Race.HUMAN

    if not profile:
        logger.error("Ghoul not found in database")
        raise ValueError("Ghoul not found in database")

    if isinstance(profile, Ghoul):
        if profile.is_dead:
            return await message.answer(
                text=dialog_service.text(key="dead_ghoul_profile", name=user.full_name)
            )

        power = ghoul_service.calculate_power(profile)
        danger_rank = ghoul_service.get_danger_rank(power)

        wins = await battle_record_service.count_wins_vs_players(profile.telegram_id)
        losses = await battle_record_service.count_losses_vs_players(
            profile.telegram_id
        )
        total_battles = await battle_record_service.count_total_battles_vs_players(
            profile.telegram_id
        )
        mob_wins = await battle_record_service.count_wins_vs_mobs(profile.telegram_id)
        mob_losses = await battle_record_service.count_losses_vs_mobs(
            profile.telegram_id
        )
        mob_battles = await battle_record_service.count_total_battles_vs_mobs(
            profile.telegram_id
        )

        rich_message = build_ghoul_profile_rich_message(
            user,
            profile,
            ghoul_service,
            danger_rank,
            power,
            wins,
            losses,
            total_battles,
            mob_wins,
            mob_losses,
            mob_battles,
        )

        try:
            return await message.answer_rich(rich_message=rich_message)
        except TelegramAPIError:
            # Свежая фича (Bot API 10.1+) - подстрахуемся старым plain-text
            # профилем на случай клиента/чата, который её не поддерживает.
            logger.warning(
                "send_rich_message failed for ghoul profile, falling back to plain text",
                exc_info=True,
            )
            fallback_text = dialog_service.text(
                key="ghoul_profile",
                name=user.full_name,
                strength=profile.strength,
                snap_count=profile.snap_count,
                kagune_type=calculate_kagune(profile.kagune_type_bit)[0].value["name"],
                health=profile.health,
                max_health=profile.max_health,
                coffee_count=profile.coffee_count,
                strength_kagune=ghoul_service.total_kagune_strength(profile),
                rc_count=profile.rc_money,
                regeneration=profile.regeneration,
                eat_ghouls=profile.eat_ghouls,
                eat_humans=profile.eat_humans,
                dexterity=profile.dexterity,
                speed=profile.speed,
                is_kakuja="Есть" if profile.is_kakuja else "Нет",
                level=profile.level,
                power=power,
                danger_rank=danger_rank,
                wins=wins,
                losses=losses,
                total_battles=total_battles,
                mob_wins=mob_wins,
                mob_losses=mob_losses,
                mob_battles=mob_battles,
            )
            return await message.answer(text=fallback_text)

    return_text = dialog_service.text(
        key="profile",
        name=user.full_name,
        race=race.value["name"],
        balance=user.balance,
    )
    return await message.answer(text=return_text)


__all__ = ["router"]
