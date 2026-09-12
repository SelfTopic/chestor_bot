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
    InputRichBlockUnion,
    InputRichMessage,
    Message,
)
from dependency_injector.wiring import Provide, inject

from src.database.models import Ghoul

from ...containers import Container
from ...game_configs import STATS
from ...services import BattleRecordService, DialogService, GhoulService, UserService
from ...types import Race
from ...utils import calculate_kagune, get_hunger_tier, level_progress_bar

logger = logging.getLogger(__name__)

router = Router(name=__name__)


def _paragraph(text: str) -> InputRichBlockParagraph:
    return InputRichBlockParagraph(text=text)


def build_ghoul_profile_rich_message(
    user,
    ghoul: Ghoul,
    ghoul_service: GhoulService,
    danger_rank: str,
    power: int,
    wins: int,
    losses: int,
    total_battles: int,
) -> InputRichMessage:
    """Собирает профиль гуля как rich-сообщение (Bot API 10.1+, aiogram
    3.29+), см. BATTLE_DESIGN.md ("UX профиля"). Блоки собираются из
    типизированных InputRichBlock*, а не из markdown-строки - синтаксис
    markdown-диалекта для sendRichMessage нигде в исходниках aiogram не
    задокументирован (только сами типы), рисковать его угадать не стали.

    "Всего боёв" из мокапа - теперь реализовано (BATTLE_ENGINE.md 5.2),
    источник - BattleRecordService.count_wins/count_losses/count_total_battles
    (таблица `battles`, всё время, не дневное окно)."""

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
        _paragraph(f"{level_progress_bar(ghoul.level_progress)} {round(ghoul.level_progress)}%"),
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
        _paragraph(f"⚔️ Всего боёв: {total_battles} ({wins} побед / {losses} поражений)"),
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
    battle_record_service: BattleRecordService = Provide[Container.battle_record_service],
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

        wins = await battle_record_service.count_wins(profile.telegram_id)
        losses = await battle_record_service.count_losses(profile.telegram_id)
        total_battles = await battle_record_service.count_total_battles(profile.telegram_id)

        rich_message = build_ghoul_profile_rich_message(
            user, profile, ghoul_service, danger_rank, power, wins, losses, total_battles
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
