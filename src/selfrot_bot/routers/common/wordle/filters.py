from typing import Any

from selfrot import BaseContext
from selfrot.filter import BaseFilter
from selfrot.types import Message

from ....context import AppContext
from ...types import UserMessage


class HasActiveWordleGame(BaseFilter[AppContext[Any]]):
    """У отправителя есть незавершённая партия wordle. О самом слове фильтр не судит:
    его форму проверяет TextRegexp, поэтому фильтры складываются через &."""

    guarantees = UserMessage

    async def check(self, ctx: BaseContext[Any]) -> bool:
        assert isinstance(ctx, AppContext)

        message = ctx.event
        if not isinstance(message, Message) or message.user is None:
            return False

        return bool(ctx.wordle_service.has_active_game(message.user.id))
