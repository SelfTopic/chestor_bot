from typing import Any

from selfrot import BaseContext
from selfrot.filter import BaseFilter
from selfrot.types import Message

from ....context import AppContext
from ...types import TextMessage
from .calculator import CalculatorError, evaluate


class Arithmetic(BaseFilter[AppContext[Any]]):
    guarantees = TextMessage

    def result(self, ctx: BaseContext[Any]) -> str | None:
        message = ctx.event
        if not isinstance(message, Message) or not message.text:
            return None

        try:
            value = evaluate(message.text, require_operator=True)
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            return str(value)
        # OverflowError у float, ValueError у str() слишком длинного int, RecursionError
        # у очень длинной цепочки унарных минусов: для пассивного фильтра это «не арифметика».
        except (CalculatorError, ArithmeticError, ValueError, RecursionError):
            return None

    async def check(self, ctx: BaseContext[Any]) -> bool:
        return self.result(ctx) is not None
