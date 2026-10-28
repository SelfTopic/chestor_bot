from typing import Any

from selfrot import MessageHandler
from selfrot.filter import Command, Text
from selfrot.types import (
    InputRichBlockDetails,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichMessage,
)

from src.bot.dialogs import Dialogs, Line
from src.bot.dialogs.vocab import KAGUNE_NAMES, STAT_NAMES
from src.bot.services.battle_engine.core import (
    KAGUNE_TYPE_MULTIPLIERS,
    KAGUNE_TYPE_PRIORITY_STAT,
)
from src.bot.types import KaguneType

from ....context import AppContext
from ...types import TextMessage
from ...rich import answer_rich_or_text, paragraph, table_cell


class KaguneInfoHandler(MessageHandler[AppContext[TextMessage]]):
    query = (
        Text("кагуне", ignore_case=True)
        | Text("kagune", ignore_case=True)
        | Command("kagune")
    )

    stat_keys = ("strength", "dexterity", "speed", "health", "regeneration")

    def paragraphs(self, line: Line) -> list[Any]:
        return [paragraph(text) for text in self.ctx.text(line).split("\n\n")]

    def build_message(self) -> InputRichMessage:
        header_row = [table_cell(self.ctx.text(Dialogs.kagune.guide.column_type()), header=True)] + [
            table_cell(self.ctx.text(STAT_NAMES[key]), header=True) for key in self.stat_keys
        ]

        rows = [header_row]
        for kagune_type in KaguneType:
            multipliers = KAGUNE_TYPE_MULTIPLIERS.get(kagune_type, {})
            row = [table_cell(self.ctx.text(KAGUNE_NAMES[kagune_type]))]
            for stat_key in self.stat_keys:
                if stat_key not in multipliers:
                    row.append(table_cell("—"))
                    continue
                mark = "★" if KAGUNE_TYPE_PRIORITY_STAT[kagune_type] == stat_key else ""
                row.append(table_cell(f"×{multipliers[stat_key]}{mark}"))
            rows.append(row)

        table = InputRichBlockTable(cells=rows, is_bordered=True, is_striped=True)

        guide = Dialogs.kagune.guide
        general_info = InputRichBlockDetails(
            summary=self.ctx.text(guide.general_title()),
            blocks=self.paragraphs(guide.general()),
        )

        blocks: list[Any] = [
            general_info,
            InputRichBlockSectionHeading(
                text=self.ctx.text(guide.table_title()), size=3
            ),
            table,
            *self.paragraphs(guide.table_notes()),
        ]

        return InputRichMessage(blocks=blocks)

    async def handle(self) -> None:
        await answer_rich_or_text(
            self.ctx.message,
            self.build_message(),
            lambda: self.ctx.text(Dialogs.kagune.info()),
            what="kagune info",
        )
