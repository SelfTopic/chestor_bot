import logging
from typing import Optional

from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.services import GhoulService, UserService
from src.bot.types import KaguneType

from ...filters import Text

router = Router(name=__name__)

logger = logging.getLogger(__name__)


@router.message(Text("топ щелк", startswith=True))
@inject
async def top_snap_handler(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    user_service: UserService = Provide[Container.user_service],
) -> None:
    count = 20

    if not message.text:
        raise

    if message.text.lower() != "топ щелк":
        count = message.text.split()[2]

        if not count.isdigit():
            await message.answer("Топ нужно указывать положительной цифрой")
            return

        count = int(count)

    if count < 1 or count > 50:
        await message.answer("Топ не может выходить за пределы значений 1-50")
        return

    top = await ghoul_service.get_top_snap(count)

    if not top:
        await message.answer("А нету топа прикинь нахуй.")
        return

    answer_text = f"Топ {count} самых сломанных пальцев\n\n"

    for c, i in enumerate(top, start=1):
        user = await user_service.get(find_by=i.telegram_id)

        answer_text += (
            f"{c}. {user.first_name if user else 'Unknown'} - {i.snap_count}\n"
        )

    await message.answer(answer_text)


# --- Топ кагуне: сумма + 4 переключаемых кнопками топа по типам ---

_CALLBACK_PREFIX = "topkagune_"

_VIEWS = ["sum", "ukaku", "koukaku", "rinkaku", "bikaku"]
_VIEW_LABELS = {"sum": "Сумма", **{kt.value["name_english"]: kt.value["name"] for kt in KaguneType}}


def _kagune_type_for_view(view: str) -> Optional[KaguneType]:
    if view == "sum":
        return None
    return next(kt for kt in KaguneType if kt.value["name_english"] == view)


def parse_top_kagune_callback_payload(payload: str) -> Optional[tuple[int, str, str]]:
    """Разбирает "<count>_<from_view>_<to_view>" -> (count, from_view, to_view),
    или None, если формат не тот. Чистая функция ради юнит-теста, см.
    parse_kagune_callback_payload в upgrade_kagune.py - тот же принцип."""

    try:
        count_str, from_view, to_view = payload.split("_", 2)
    except ValueError:
        return None

    if not count_str.isdigit():
        return None

    if from_view not in _VIEWS or to_view not in _VIEWS:
        return None

    return int(count_str), from_view, to_view


def _build_top_kagune_keyboard(
    current: str, previous: Optional[str], count: int
) -> InlineKeyboardMarkup:
    """Кнопка на месте текущего вида не нужна (бессмысленно жать "то, что и
    так открыто") - вместо этого на месте вида, с которого только что
    переключились, показывается кнопка "назад", а не обычная кнопка типа."""

    buttons = []
    for view in _VIEWS:
        if view == current:
            continue
        label = _VIEW_LABELS[view]
        if view == previous:
            label = f"⬅️ {label}"
        buttons.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"{_CALLBACK_PREFIX}{count}_{current}_{view}",
            )
        )

    return InlineKeyboardMarkup(inline_keyboard=[buttons])


async def _render_top_kagune(
    ghoul_service: GhoulService,
    user_service: UserService,
    current: str,
    previous: Optional[str],
    count: int,
) -> tuple[str, InlineKeyboardMarkup]:
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
        lines = [heading, ""]
        for c, ghoul in enumerate(top, start=1):
            user = await user_service.get(find_by=ghoul.telegram_id)
            value = (
                ghoul_service.total_kagune_strength(ghoul)
                if kagune_type is None
                else ghoul_service.get_kagune_strength(ghoul, kagune_type)
            )
            lines.append(f"{c}. {user.first_name if user else 'Unknown'} - {value}")
        text = "\n".join(lines)

    keyboard = _build_top_kagune_keyboard(current=current, previous=previous, count=count)
    return text, keyboard


@router.message(Text("топ кагуне", startswith=True))
@inject
async def top_kagune_handler(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    user_service: UserService = Provide[Container.user_service],
) -> None:
    count = 20

    if not message.text:
        raise

    if message.text.lower() != "топ кагуне":
        count = message.text.split()[2]

        if not count.isdigit():
            await message.answer("Топ нужно указывать положительной цифрой")
            return

        count = int(count)

    if count < 1 or count > 50:
        await message.answer("Топ не может выходить за пределы значений 1-50")
        return

    text, keyboard = await _render_top_kagune(
        ghoul_service, user_service, current="sum", previous=None, count=count
    )
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(lambda c: c.data and c.data.startswith(_CALLBACK_PREFIX))
@inject
async def top_kagune_callback(
    callback_query: CallbackQuery,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    user_service: UserService = Provide[Container.user_service],
) -> None:
    if not callback_query.data or not isinstance(callback_query.message, Message):
        await callback_query.answer("Невозможно обработать запрос")
        return

    parsed = parse_top_kagune_callback_payload(
        callback_query.data[len(_CALLBACK_PREFIX) :]
    )
    if parsed is None:
        await callback_query.answer("Неверные данные кнопки")
        return

    count, from_view, to_view = parsed

    text, keyboard = await _render_top_kagune(
        ghoul_service, user_service, current=to_view, previous=from_view, count=count
    )
    await callback_query.message.edit_text(text=text, reply_markup=keyboard)
    await callback_query.answer()


__all__ = ["router"]
