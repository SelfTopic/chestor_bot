from selfrot.types import (
    InputRichBlockDivider,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichBlock,
    InputRichMessage,
)

from typing import Any

from src.bot.dialogs import Dialogs
from src.bot.dialogs.vocab import STAT_NAMES
from src.bot.services import BattleEngine, GhoulService
from src.bot.services.battle_engine.core import StatBreakdown, compute_stat_breakdown
from src.bot.utils import get_hunger_tier
from src.database.models import Ghoul, User

from ....context import AppContext
from ...rich import paragraph, table_cell

_STAT_KEYS = ("strength", "dexterity", "speed", "health", "regeneration")


def _fmt(value: float) -> str:
    return str(round(value, 1))


def combat_power_rich(
    ctx: AppContext[Any],
    user: User,
    ghoul: Ghoul,
    danger_rank: str,
    ghoul_service: GhoulService,
    engine: BattleEngine,
) -> InputRichMessage:
    fighter = engine.ghoul_to_fighter(ghoul, user.full_name, ghoul_service)
    breakdown: dict[str, StatBreakdown] = compute_stat_breakdown(fighter.snapshot)

    vacuum_kagune = ghoul_service.total_kagune_strength(ghoul)
    vacuum_power = ghoul_service.calculate_power(ghoul)
    combat_base_power = engine.power_of(fighter.snapshot)
    effective_power = engine.effective_power_of(fighter.stats)

    phrases = Dialogs.combat_power.rich
    stat_header = ctx.text(phrases.column_stat())
    value_header = ctx.text(phrases.column_value())
    kagune_label = ctx.text(phrases.kagune_row())
    total_label = ctx.text(phrases.total_row())

    vacuum_values = {
        "strength": ghoul.strength,
        "dexterity": ghoul.dexterity,
        "speed": ghoul.speed,
        "health": ghoul.max_health,
        "regeneration": ghoul.regeneration,
    }
    vacuum_rows = [
        [table_cell(ctx.text(STAT_NAMES[key])), table_cell(str(vacuum_values[key]))]
        for key in _STAT_KEYS
    ]
    vacuum_rows.append([table_cell(kagune_label), table_cell(str(vacuum_kagune))])
    vacuum_rows.append([table_cell(total_label), table_cell(str(vacuum_power))])

    vacuum_table = InputRichBlockTable(
        cells=[
            [table_cell(stat_header, header=True), table_cell(value_header, header=True)],
            *vacuum_rows,
        ],
        is_bordered=True,
        is_striped=True,
    )

    combat_rows = [
        [
            table_cell(ctx.text(STAT_NAMES[key])),
            table_cell(_fmt(breakdown[key].base)),
            table_cell(_fmt(breakdown[key].after_hunger)),
            table_cell(_fmt(breakdown[key].after_kagune)),
        ]
        for key in _STAT_KEYS
    ]

    tier = get_hunger_tier(ghoul.hunger)
    kagune_after_hunger = vacuum_kagune * tier.rising_multiplier
    combat_rows.append(
        [
            table_cell(kagune_label),
            table_cell(str(vacuum_kagune)),
            table_cell(_fmt(kagune_after_hunger)),
            table_cell(_fmt(fighter.stats.kagune_strength)),
        ]
    )

    combat_total_after_hunger = (
        sum(breakdown[key].after_hunger for key in _STAT_KEYS)
        + kagune_after_hunger
    )
    combat_rows.append(
        [
            table_cell(total_label),
            table_cell(str(round(combat_base_power))),
            table_cell(_fmt(combat_total_after_hunger)),
            table_cell(_fmt(effective_power)),
        ]
    )

    combat_table = InputRichBlockTable(
        cells=[
            [
                table_cell(stat_header, header=True),
                table_cell(value_header, header=True),
                table_cell(ctx.text(phrases.column_hunger()), header=True),
                table_cell(ctx.text(phrases.column_kagune()), header=True),
            ],
            *combat_rows,
        ],
        is_bordered=True,
        is_striped=True,
    )

    blocks: list[InputRichBlock] = [
        InputRichBlockSectionHeading(
            text=ctx.text(phrases.title(danger_rank=danger_rank, name=user.full_name)),
            size=3,
        ),
        vacuum_table,
        InputRichBlockDivider(),
        paragraph(ctx.text(phrases.combat_note())),
        combat_table,
        InputRichBlockDivider(),
        *(paragraph(text) for text in ctx.text(phrases.hints()).split("\n\n")),
    ]

    return InputRichMessage(blocks=blocks)
