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

from src.bot.dialogs import Dialogs, Line
from src.bot.dialogs.vocab import HUNGER_NAMES, KAGUNE_NAMES, STAT_NAMES
from src.bot.game_configs import STATS
from src.bot.services import GhoulService
from src.bot.utils import calculate_kagune, get_hunger_tier, level_progress_bar
from src.database.models import Ghoul, User

from ....context import AppContext
from ...rich import paragraph


@dataclass(frozen=True)
class BattleStats:
    wins: int
    losses: int
    total: int
    mob_wins: int
    mob_losses: int
    mob_total: int


def kakuja_status(ghoul: Ghoul) -> Line:
    phrases = Dialogs.ghoul.rich_profile
    return phrases.kakuja_yes() if ghoul.is_kakuja else phrases.kakuja_no()


def rich_profile(
    ctx: AppContext[Any],
    user: User,
    ghoul: Ghoul,
    ghoul_service: GhoulService,
    danger_rank: str,
    power: int,
    stats: BattleStats,
) -> InputRichMessage:
    tier = get_hunger_tier(ghoul.hunger)
    phrases = Dialogs.ghoul.rich_profile

    def line(phrase: Line) -> Any:
        return paragraph(ctx.text(phrase))

    def item(phrase: Line) -> InputRichBlockListItem:
        return InputRichBlockListItem(blocks=[line(phrase)])

    kagune_items = [
        item(
            phrases.kagune_row(
                kagune=KAGUNE_NAMES[kagune_type],
                strength=ghoul_service.get_kagune_strength(ghoul, kagune_type),
            )
        )
        for kagune_type in ghoul_service.owned_kagune_types(ghoul)
    ]

    stat_items = [
        item(phrases.stat_row(stat=STAT_NAMES[key], value=getattr(ghoul, key)))
        for key, _emoji in STATS
        if key != "max_health"
    ]

    blocks: list[Any] = [
        InputRichBlockSectionHeading(
            text=ctx.text(phrases.title(danger_rank=danger_rank, name=user.full_name)),
            size=3,
        ),
        line(phrases.level(level=ghoul.level)),
        paragraph(
            f"{level_progress_bar(ghoul.level_progress)} {round(ghoul.level_progress)}%"
        ),
        line(phrases.hunger(hunger=ghoul.hunger, tier=HUNGER_NAMES[tier.key])),
        line(phrases.rc(rc=ghoul.rc_money)),
        InputRichBlockDetails(
            summary=ctx.text(phrases.kagune_types()),
            blocks=[InputRichBlockList(items=kagune_items)],
        ),
        line(phrases.snaps(count=ghoul.snap_count)),
        line(phrases.coffee(count=ghoul.coffee_count)),
        line(phrases.humans(count=ghoul.eat_humans)),
        InputRichBlockDetails(
            summary=ctx.text(phrases.stats()),
            blocks=[
                InputRichBlockList(items=stat_items),
                line(phrases.health(health=ghoul.health, max_health=ghoul.max_health)),
                line(phrases.power(power=power)),
            ],
        ),
        line(phrases.ghouls(count=ghoul.eat_ghouls)),
        line(phrases.fights(total=stats.total, wins=stats.wins, losses=stats.losses)),
        line(
            phrases.mob_fights(
                total=stats.mob_total, wins=stats.mob_wins, losses=stats.mob_losses
            )
        ),
        InputRichBlockDivider(),
        line(phrases.kakuja(status=kakuja_status(ghoul))),
        line(phrases.deaths(count=ghoul.deaths)),
    ]

    return InputRichMessage(blocks=blocks)


def plain_profile(
    ctx: AppContext[Any],
    user: User,
    ghoul: Ghoul,
    ghoul_service: GhoulService,
    danger_rank: str,
    power: int,
    stats: BattleStats,
) -> str:
    return ctx.text(
        Dialogs.ghoul.profile(
            name=user.full_name,
            strength=ghoul.strength,
            snap_count=ghoul.snap_count,
            kagune_type=KAGUNE_NAMES[calculate_kagune(ghoul.kagune_type_bit)[0]],
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
            is_kakuja=kakuja_status(ghoul),
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
    )
