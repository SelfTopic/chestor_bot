"""
Rich-сообщение "боевой мощи" (BATTLE_ENGINE.md 8.4): две таблицы рядом.
"Фиктивная" — вакуумные (паспортные) статы, те же числа, что суммирует
GhoulService.calculate_power. "Боевая" — путь стата: значение → влияние голода →
влияние кагуне; правый столбец участвует в бою прямо сейчас (EffectiveStats).

Здоровье — особый случай: в "фиктивной" таблице ghoul.max_health (паспортный
потолок), в "боевой" базой идёт текущее ghoul.health, с которым боец входит в бой.
Перенесено из прод-combat_power.py почти дословно, на типах selfrot.
"""

from selfrot.types import (
    InputRichBlockDivider,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichBlock,
    InputRichMessage,
)

from src.bot.services import BattleService, GhoulService
from src.bot.services.battle_engine.core import StatBreakdown, compute_stat_breakdown
from src.bot.utils import get_hunger_tier
from src.database.models import Ghoul, User

from ...common.race_profile.rich import paragraph, table_cell

# Порядок статов как STATS в game_configs.py; max_health здесь и есть "Здоровье".
_STAT_LABELS: list[tuple[str, str]] = [
    ("strength", "Сила"),
    ("dexterity", "Ловкость"),
    ("speed", "Скорость"),
    ("health", "Здоровье"),
    ("regeneration", "Регенерация"),
]


def _fmt(value: float) -> str:
    return str(round(value, 1))


def combat_power_rich(
    user: User,
    ghoul: Ghoul,
    danger_rank: str,
    ghoul_service: GhoulService,
    engine: BattleService,
) -> InputRichMessage:
    fighter = engine.ghoul_to_fighter(ghoul, user.full_name, ghoul_service)
    breakdown: dict[str, StatBreakdown] = compute_stat_breakdown(fighter.snapshot)

    vacuum_kagune = ghoul_service.total_kagune_strength(ghoul)
    vacuum_power = ghoul_service.calculate_power(ghoul)
    combat_base_power = engine.power_of(fighter.snapshot)
    effective_power = engine.effective_power_of(fighter.stats)

    vacuum_values = {
        "strength": ghoul.strength,
        "dexterity": ghoul.dexterity,
        "speed": ghoul.speed,
        "health": ghoul.max_health,
        "regeneration": ghoul.regeneration,
    }
    vacuum_rows = [
        [table_cell(label), table_cell(str(vacuum_values[key]))]
        for key, label in _STAT_LABELS
    ]
    vacuum_rows.append([table_cell("Кагуне"), table_cell(str(vacuum_kagune))])
    vacuum_rows.append([table_cell("Итого"), table_cell(str(vacuum_power))])

    vacuum_table = InputRichBlockTable(
        cells=[
            [table_cell("Стат", header=True), table_cell("Значение", header=True)],
            *vacuum_rows,
        ],
        is_bordered=True,
        is_striped=True,
    )

    combat_rows = [
        [
            table_cell(label),
            table_cell(_fmt(breakdown[key].base)),
            table_cell(_fmt(breakdown[key].after_hunger)),
            table_cell(_fmt(breakdown[key].after_kagune)),
        ]
        for key, label in _STAT_LABELS
    ]

    # Сила кагуне не идёт через типовой множитель (см. compute_effective_stats):
    # "влияние голода" и "влияние кагуне" совпадают, если гуль не какудзя.
    tier = get_hunger_tier(ghoul.hunger)
    kagune_after_hunger = vacuum_kagune * tier.rising_multiplier
    combat_rows.append(
        [
            table_cell("Кагуне"),
            table_cell(str(vacuum_kagune)),
            table_cell(_fmt(kagune_after_hunger)),
            table_cell(_fmt(fighter.stats.kagune_strength)),
        ]
    )

    combat_total_after_hunger = (
        sum(breakdown[key].after_hunger for key, _ in _STAT_LABELS)
        + kagune_after_hunger
    )
    combat_rows.append(
        [
            table_cell("Итого"),
            table_cell(str(round(combat_base_power))),
            table_cell(_fmt(combat_total_after_hunger)),
            table_cell(_fmt(effective_power)),
        ]
    )

    combat_table = InputRichBlockTable(
        cells=[
            [
                table_cell("Стат", header=True),
                table_cell("Значение", header=True),
                table_cell("Влияние голода", header=True),
                table_cell("Влияние кагуне", header=True),
            ],
            *combat_rows,
        ],
        is_bordered=True,
        is_striped=True,
    )

    blocks: list[InputRichBlock] = [
        InputRichBlockSectionHeading(
            text=f"⚡ Боевая мощь гуля {danger_rank} ранга {user.full_name}", size=3
        ),
        vacuum_table,
        InputRichBlockDivider(),
        paragraph(
            "Самое правое значение в таблице ниже - значение, которое реально "
            "будет использоваться в бою."
        ),
        combat_table,
        InputRichBlockDivider(),
        paragraph('Если надо узнать, как голод влияет на статистики - напиши "голод".'),
        paragraph(
            "Если надо узнать, как кагуне влияет на статистики - используй /kagune."
        ),
    ]

    return InputRichMessage(blocks=blocks)
