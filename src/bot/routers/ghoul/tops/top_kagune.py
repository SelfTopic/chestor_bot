from typing import Any, get_args

from selfrot import BaseRouter, InlineKeyboard, MessageHandler
from selfrot.filter import CallbackDataStartswith
from selfrot.handlers import CallbackQueryHandler
from selfrot.keyboard import button
from selfrot.types import DataCallbackQuery, InlineKeyboardMarkup, Message, TextMessage

from src.bot.dialogs import Dialogs
from src.bot.types import KaguneType

from ....context import AppContext
from .callback_data import TopKaguneView, ViewName
from .count import GhoulTopHandler, top_command, top_row, top_text

_VIEWS: tuple[ViewName, ...] = get_args(ViewName)
_KAGUNE_LABELS: dict[ViewName, str] = {
    kt.value["name_english"]: kt.value["name"] for kt in KaguneType
}


def _view_label(ctx: AppContext[Any], view: ViewName) -> str:
    if view == "sum":
        return ctx.text(Dialogs.tops.kagune.sum_button())
    return _KAGUNE_LABELS[view]


def _kagune_type_for_view(view: ViewName) -> KaguneType | None:
    if view == "sum":
        return None
    return next(kt for kt in KaguneType if kt.value["name_english"] == view)


def _build_keyboard(
    ctx: AppContext[Any], current: ViewName, previous: ViewName | None, count: int
) -> InlineKeyboardMarkup:
    buttons = []
    for view in _VIEWS:
        if view == current:
            continue
        label = _view_label(ctx, view)
        if view == previous:
            label = f"⬅️ {label}"
        buttons.append(
            button(label, TopKaguneView(count=count, from_view=current, to_view=view))
        )

    return InlineKeyboard().row(*buttons).markup()


async def _render(
    ctx: AppContext[Any], current: ViewName, previous: ViewName | None, count: int
) -> tuple[str, InlineKeyboardMarkup]:
    ghoul_service = ctx.ghoul_service
    kagune_type = _kagune_type_for_view(current)
    top = await ghoul_service.get_top_kagune(count, kagune_type)

    heading = (
        Dialogs.tops.kagune.sum_title(count=count)
        if kagune_type is None
        else Dialogs.tops.kagune.type_title(
            count=count, kagune=_view_label(ctx, current)
        )
    )

    names = await ctx.first_names([ghoul.telegram_id for ghoul in top])
    rows = [
        top_row(
            ctx,
            place,
            names.get(ghoul.telegram_id),
            ghoul_service.total_kagune_strength(ghoul)
            if kagune_type is None
            else ghoul_service.get_kagune_strength(ghoul, kagune_type),
        )
        for place, ghoul in enumerate(top, start=1)
    ]
    text = top_text(ctx, ctx.text(heading), rows)

    return text, _build_keyboard(ctx, current=current, previous=previous, count=count)


class TopKaguneHandler(GhoulTopHandler, MessageHandler[AppContext[TextMessage]]):
    cmd = top_command("топ кагуне")
    query = cmd

    async def show(self, count: int) -> None:
        body, keyboard = await _render(
            self.ctx, current="sum", previous=None, count=count
        )
        await self.ctx.message.answer(body, reply_markup=keyboard)


class TopKaguneViewHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    press = TopKaguneView.filter()
    query = press

    async def handle(self) -> None:
        ctx = self.ctx
        message = ctx.callback_query.message

        if not isinstance(message, Message):
            await ctx.callback_query.answer(ctx.text(Dialogs.errors.cannot_process()))
            return

        payload = self.press.parse(ctx)

        body, keyboard = await _render(
            ctx,
            current=payload.to_view,
            previous=payload.from_view,
            count=payload.count,
        )
        await message.edit_text(text=body, reply_markup=keyboard)
        await ctx.callback_query.answer()


class TopKaguneBadDataHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    query = CallbackDataStartswith("topkagune")

    async def handle(self) -> None:
        await self.ctx.callback_query.answer(
            self.ctx.text(Dialogs.tops.kagune.bad_button())
        )


class TopKaguneRouter(BaseRouter[AppContext]):
    handlers = (TopKaguneHandler, TopKaguneViewHandler, TopKaguneBadDataHandler)
