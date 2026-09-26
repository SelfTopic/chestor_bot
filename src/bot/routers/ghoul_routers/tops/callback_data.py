from typing import Literal

from selfrot import CallbackPayload

ViewName = Literal["sum", "ukaku", "koukaku", "rinkaku", "bikaku"]


class TopKaguneView(CallbackPayload, prefix="topkagune"):
    """Переключение вкладки топа кагуне. Заменяет ручной
    parse_top_kagune_callback_payload(payload) у прода — типы и формат
    (from_view/to_view — один из пяти видов) проверяет unpack() сам."""

    count: int
    from_view: ViewName
    to_view: ViewName
