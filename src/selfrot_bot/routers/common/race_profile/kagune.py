from typing import Any

from selfrot import MessageHandler
from selfrot.filter import Command, Text
from selfrot.types import (
    InputRichBlockDetails,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichMessage,
)

from src.bot.services.battle_engine.core import (
    KAGUNE_TYPE_MULTIPLIERS,
    KAGUNE_TYPE_PRIORITY_STAT,
)
from src.bot.types import KaguneType

from ....context import AppContext
from ....types import TextMessage
from .rich import answer_rich_or_text, paragraph, table_cell


class KaguneInfoHandler(MessageHandler[AppContext[TextMessage]]):
    query = Text("кагуне", ignore_case=True) | Command("kagune")

    # Порядок и подписи статов в таблице влияния кагуне: тот же, что в "боевая мощь".
    stat_labels: list[tuple[str, str]] = [
        ("strength", "Сила"),
        ("dexterity", "Ловкость"),
        ("speed", "Скорость"),
        ("health", "Здоровье"),
        ("regeneration", "Регенерация"),
    ]

    def build_message(self) -> InputRichMessage:
        """Справочная таблица "какой тип кагуне на какой стат и с каким множителем
        влияет" (BATTLE_DESIGN.md "Множители типов кагуне"); не привязана к гулю."""

        header_row = [table_cell("Тип", header=True)] + [
            table_cell(label, header=True) for _, label in self.stat_labels
        ]

        rows = [header_row]
        for kagune_type in KaguneType:
            multipliers = KAGUNE_TYPE_MULTIPLIERS.get(kagune_type, {})
            row = [table_cell(str(kagune_type.value["name"]))]
            for stat_key, _ in self.stat_labels:
                if stat_key not in multipliers:
                    row.append(table_cell("—"))
                    continue
                mark = "★" if KAGUNE_TYPE_PRIORITY_STAT[kagune_type] == stat_key else ""
                row.append(table_cell(f"×{multipliers[stat_key]}{mark}"))
            rows.append(row)

        table = InputRichBlockTable(cells=rows, is_bordered=True, is_striped=True)

        general_info = InputRichBlockDetails(
            summary="📖 Общая информация о кагуне",
            blocks=[
                paragraph(
                    "Какухо - орган в теле гуля, управляющий RC-клетками: "
                    "регенерация, усиление тела и кагуне вне тела. Его "
                    "расположение определяет боевой стиль каждого типа."
                ),
                paragraph(
                    "🔸 Укаку (плечи): приток RC в мозг и руки - высокая "
                    "скорость, частые лёгкие удары. Минус - низкая выносливость, "
                    "однообразие легко пережидается."
                ),
                paragraph(
                    "🔸 Коукаку (лопатки): RC усиливает мышцы спины и рук - "
                    "мощный физический удар. Минус - низкая скорость, ловкий "
                    "противник уворачивается и контратакует."
                ),
                paragraph(
                    "🔸 Ринкаку (поясница): RC равномерно расходится по телу - "
                    "высокая выносливость и регенерация. Явных слабостей почти "
                    "нет."
                ),
                paragraph(
                    "🔸 Бикаку (копчик): RC концентрируется в корпусе и ногах - "
                    "понемногу всех усилений сразу, универсал без выраженного "
                    "минуса."
                ),
                paragraph(
                    "Как это влияет на урон: каждый удар решается монеткой "
                    "«физический / кагуне» - первый удар боя всегда физический, "
                    "дальше шанс физического падает на 10 п.п. за каждый "
                    "нанесённый физический удар (бой постепенно скатывается в "
                    "удары кагуне). Урон кагуне обычно выше - считается от силы "
                    "И силы кагуне вместе, физический - только от силы."
                ),
                paragraph(
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

        blocks: list[Any] = [
            general_info,
            InputRichBlockSectionHeading(
                text="♦️ Влияние типов кагуне на статы", size=3
            ),
            table,
            paragraph(
                "★ - приоритетный стат типа: если открыто несколько типов, "
                "трогающих один стат, побеждает «хозяин» (★), иначе берётся "
                "наименьший из множителей (правило стаков, см. BATTLE_DESIGN.md)."
            ),
            paragraph(
                "Сила кагуне (сумма силы всех открытых типов) сама по себе НЕ "
                "множится типом кагуне - только голодом (растущий стат) и "
                "какуджей."
            ),
        ]

        return InputRichMessage(blocks=blocks)

    async def handle(self) -> None:
        await answer_rich_or_text(
            self.ctx.message,
            self.build_message(),
            lambda: self.ctx.dialog_service.text(key="kagune_info"),
            what="kagune info",
        )
