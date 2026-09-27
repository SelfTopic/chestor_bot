from typing import Any

from selfrot import BaseContext
from selfrot.filter import BaseFilter
from selfrot.types import Message

from ....context import AppContext
from ...types import TextMessage
from .calculator import DivisionByZero, NotArithmetic, Number, ResultTooBig, evaluate

Outcome = Number | DivisionByZero | ResultTooBig


class Arithmetic(BaseFilter[AppContext[Any]]):
    guarantees = TextMessage

    def outcome(self, ctx: BaseContext[Any]) -> Outcome | None:
        message = ctx.event
        if not isinstance(message, Message) or not message.text:
            return None

        try:
            return evaluate(message.text, require_operator=True)
        # Арифметика, которую нельзя посчитать, тоже заслуживает ответа — пасхалкой.
        except (DivisionByZero, ResultTooBig) as failure:
            return failure
        except NotArithmetic:
            return None

    async def check(self, ctx: BaseContext[Any]) -> bool:
        return self.outcome(ctx) is not None
