"""
"топ кагуне [N]": сумма + 4 переключаемых кнопками топа по типам. Кнопка на месте
текущего вида не нужна (бессмысленно жать "то, что и так открыто") — вместо неё на
месте вида, с которого только что переключились, показывается кнопка "назад".
"""

from typing import Any, get_args

from selfrot import BaseRouter, InlineKeyboard, MessageHandler
from selfrot.filter import CallbackDataStartswith
from selfrot.handlers import CallbackQueryHandler
from selfrot.keyboard import button
from selfrot.types import DataCallbackQuery, InlineKeyboardMarkup, Message, TextMessage

from src.bot.types import KaguneType

from ....context import AppContext
from .callback_data import TopKaguneView, ViewName
from .count import GhoulTopHandler, top_command

_VIEWS: tuple[ViewName, ...] = get_args(ViewName)
_VIEW_LABELS: dict[ViewName, str] = {
    "sum": "Сумма",
    **{kt.value["name_english"]: kt.value["name"] for kt in KaguneType},
}


def _kagune_type_for_view(view: ViewName) -> KaguneType | None:
    if view == "sum":
        return None
    return next(kt for kt in KaguneType if kt.value["name_english"] == view)


def _build_keyboard(
    current: ViewName, previous: ViewName | None, count: int
) -> InlineKeyboardMarkup:
    buttons = []
    for view in _VIEWS:
        if view == current:
            continue
        label = _VIEW_LABELS[view]
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

    label = _VIEW_LABELS[current]
    heading = (
        f"Топ {count} самых сильных кагуне в сумме"
        if kagune_type is None
        else f"Топ {count} самых сильных кагуне: {label}"
    )

    if not top:
        text = f"{heading}\n\nА нету топа прикинь нахуй."
    else:
        names = await ctx.first_names([ghoul.telegram_id for ghoul in top])
        lines = [heading, ""]
        for place, ghoul in enumerate(top, start=1):
            name = names.get(ghoul.telegram_id, "Unknown")
            value = (
                ghoul_service.total_kagune_strength(ghoul)
                if kagune_type is None
                else ghoul_service.get_kagune_strength(ghoul, kagune_type)
            )
            lines.append(f"{place}. {name} - {value}")
        text = "\n".join(lines)

    return text, _build_keyboard(current=current, previous=previous, count=count)


class TopKaguneHandler(GhoulTopHandler, MessageHandler[AppContext[TextMessage]]):
    cmd = top_command("топ кагуне")
    query = cmd

    async def show(self, count: int) -> None:
        body, keyboard = await _render(self.ctx, current="sum", previous=None, count=count)
        await self.ctx.message.answer(body, reply_markup=keyboard)


class TopKaguneViewHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    press = TopKaguneView.filter()
    query = press

    async def handle(self) -> None:
        ctx = self.ctx
        message = ctx.callback_query.message

        if not isinstance(message, Message):
            await ctx.callback_query.answer("Невозможно обработать запрос")
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
    """Кнопка топа, данные которой не разобрались, как у прода."""

    query = CallbackDataStartswith("topkagune")

    async def handle(self) -> None:
        await self.ctx.callback_query.answer("Неверные данные кнопки")


class TopKaguneRouter(BaseRouter[AppContext]):
    handlers = (TopKaguneHandler, TopKaguneViewHandler, TopKaguneBadDataHandler)
