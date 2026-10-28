from typing import Any

from selfrot import InlineKeyboard
from selfrot.types import (
    InlineKeyboardMarkup,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichMessage,
)

from src.bot.dialogs import Dialogs
from src.bot.dialogs.vocab import KAGUNE_NAMES
from src.bot.game_configs import EVOLUTION_CONFIG
from src.bot.types import KaguneType
from src.bot.utils import format_amount
from src.database.models import Ghoul

from ....context import AppContext
from ...rich import table_cell
from .payloads import BecomeKakujaPress, BuyKagunePress

EVOLUTION = Dialogs.kagune.evolution


def _status_rows(ctx: AppContext[Any], ghoul: Ghoul) -> list[str]:
    ghoul_service = ctx.ghoul_service
    rows = []
    for kagune_type in KaguneType:
        strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
        status = (
            ctx.text(EVOLUTION.owned(strength=strength))
            if strength is not None
            else ctx.text(EVOLUTION.not_owned())
        )
        rows.append((ctx.text(KAGUNE_NAMES[kagune_type]), status))

    kakuja_status = ctx.text(EVOLUTION.kakuja_yes() if ghoul.is_kakuja else EVOLUTION.kakuja_no())
    rows.append((ctx.text(EVOLUTION.kakuja_row()), kakuja_status))
    return rows


def _keyboard(ctx: AppContext[Any], ghoul: Ghoul, invoker_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboard()
    missing = ctx.ghoul_service.next_missing_kagune_type(ghoul)
    if missing is not None:
        label = EVOLUTION.buy_kagune_button(
            kagune=KAGUNE_NAMES[missing],
            cheston=format_amount(EVOLUTION_CONFIG.new_kagune_cheston),
            rc=format_amount(EVOLUTION_CONFIG.new_kagune_rc),
        )
        keyboard.button(ctx.text(label), BuyKagunePress(invoker_id=invoker_id))

    if not ghoul.is_kakuja:
        label = EVOLUTION.buy_kakuja_button(
            cheston=format_amount(EVOLUTION_CONFIG.kakuja_cheston),
            rc=format_amount(EVOLUTION_CONFIG.kakuja_rc),
        )
        keyboard.button(ctx.text(label), BecomeKakujaPress(invoker_id=invoker_id))

    return keyboard.markup()


def build_rich(ctx: AppContext[Any], ghoul: Ghoul) -> InputRichMessage:
    header = [
        table_cell(ctx.text(EVOLUTION.column_type()), header=True),
        table_cell(ctx.text(EVOLUTION.column_status()), header=True),
    ]
    cells = [header, *([table_cell(name), table_cell(status)] for name, status in _status_rows(ctx, ghoul))]
    return InputRichMessage(
        blocks=[
            InputRichBlockSectionHeading(text=ctx.text(EVOLUTION.title()), size=3),
            InputRichBlockTable(cells=cells, is_bordered=True, is_striped=True),
            InputRichBlockParagraph(text=ctx.text(EVOLUTION.warning())),
        ]
    )


def build_plain(ctx: AppContext[Any], ghoul: Ghoul) -> str:
    rows = [f"{name}: {status}" for name, status in _status_rows(ctx, ghoul)]
    return "\n".join([ctx.text(EVOLUTION.title()), *rows, ctx.text(EVOLUTION.warning())])


def build_menu(
    ctx: AppContext[Any], ghoul: Ghoul, invoker_id: int
) -> tuple[InputRichMessage, str, InlineKeyboardMarkup]:
    return build_rich(ctx, ghoul), build_plain(ctx, ghoul), _keyboard(ctx, ghoul, invoker_id)
