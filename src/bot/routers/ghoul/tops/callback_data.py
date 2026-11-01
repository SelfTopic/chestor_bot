from typing import Literal

from selfrot import CallbackPayload

ViewName = Literal["sum", "ukaku", "koukaku", "rinkaku", "bikaku"]


class TopKaguneView(CallbackPayload, prefix="topkagune"):
    count: int
    from_view: ViewName
    to_view: ViewName


# Отдельный префикс, а не поле: кнопки уже отправленных топов не знают о новом поле.
class TopKaguneChatView(TopKaguneView, prefix="topkagunechat"):
    pass
