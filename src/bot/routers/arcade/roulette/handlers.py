import logging
from typing import Generic, TypeVar

from selfrot import CommandArgs, MessageHandler
from selfrot.exceptions import CommandArgsError
from selfrot.filter import AnyCommand, Command, HasMessageCallbackQuery, HasUser
from selfrot.handlers import CallbackQueryHandler

from src.bot.dialogs import Dialogs, Line
from src.bot.dialogs.vocab import DEP_COLOR_NAMES
from src.bot.exceptions import (
    RouletteBetOutOfRange,
    RouletteBusy,
    RouletteNoChoice,
    RouletteNoMachine,
    RouletteNotEnoughMoney,
    RouletteNotYours,
    UnknownLotteryColor,
)
from src.bot.services.roulette.spins import parse_color
from src.bot.utils import format_amount

from ....context import AppContext
from ...types import DataMessageCallbackQuery, TextUserMessage
from .payloads import AmountPress, ColorPress, HintPress, SpinPress
from .screen import COLORS

logger = logging.getLogger(__name__)

ROULETTE = Dialogs.roulette
TContext = TypeVar("TContext", bound=AppContext[DataMessageCallbackQuery])


def range_line(exc: RouletteBetOutOfRange) -> Line:
    return ROULETTE.bet_out_of_range(
        min_bet=format_amount(exc.min_bet), max_bet=format_amount(exc.max_bet)
    )


class OpenArgs(CommandArgs):
    color: str | None = None
    amount: int | None = None


class OpenRouletteHandler(MessageHandler[AppContext[TextUserMessage]]):
    cmd = AnyCommand(
        Command("депнуть", OpenArgs, prefixes="", ignore_case=True),
        Command("ставка", OpenArgs, prefixes="", ignore_case=True),
        Command("bet", OpenArgs, prefixes="", ignore_case=True),
    )
    query = cmd & HasUser()

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        color = None if args.color is None else parse_color(args.color)
        message = self.ctx.message
        await self.ctx.roulette_service.open(message.chat.id, message.user.id, color, args.amount)

    def error_line(self, exc: Exception) -> Line:
        match exc:
            case CommandArgsError():
                return ROULETTE.usage()
            case UnknownLotteryColor(color=color):
                colors = ", ".join(self.ctx.text(DEP_COLOR_NAMES[c]) for c in COLORS)
                return ROULETTE.unknown_color(color=color, colors=colors)
            case RouletteBetOutOfRange():
                return range_line(exc)
            case RouletteBusy():
                return ROULETTE.busy()
            case _:
                logger.error("Автомат рулетки не открылся", exc_info=exc)
                return ROULETTE.failed()

    async def on_error(self, exc: Exception) -> None:
        await self.ctx.say(self.error_line(exc), reply=True)


# Нажатие правит само сообщение автомата, поэтому всплывашка — только для ошибок.
class RoulettePressHandler(CallbackQueryHandler[TContext], Generic[TContext]):
    @property
    def user_id(self) -> int:
        return self.ctx.callback_query.user.id

    async def handle(self) -> None:
        await self.press()
        await self.ctx.callback_query.answer()

    async def press(self) -> None:
        raise NotImplementedError

    def error_line(self, exc: Exception) -> Line | None:
        match exc:
            case RouletteNoMachine():
                return ROULETTE.machine_closed()
            case RouletteNotYours():
                return ROULETTE.not_yours()
            case RouletteBusy():
                return ROULETTE.busy()
            case RouletteNoChoice():
                return ROULETTE.no_choice()
            case RouletteNotEnoughMoney():
                return ROULETTE.not_enough_money()
            case RouletteBetOutOfRange():
                return range_line(exc)
            case _:
                return None

    async def on_error(self, exc: Exception) -> None:
        line = self.error_line(exc)
        if line is None:
            raise exc
        await self.ctx.callback_query.answer(self.ctx.text(line), show_alert=True)


class ColorHandler(RoulettePressHandler[AppContext[DataMessageCallbackQuery]]):
    payload = ColorPress.filter()
    query = payload & HasMessageCallbackQuery()

    async def press(self) -> None:
        pressed = self.payload.parse(self.ctx)
        color = COLORS[pressed.color]
        await self.ctx.roulette_service.choose(pressed.machine, self.user_id, color=color)


class AmountHandler(RoulettePressHandler[AppContext[DataMessageCallbackQuery]]):
    payload = AmountPress.filter()
    query = payload & HasMessageCallbackQuery()

    async def press(self) -> None:
        pressed = self.payload.parse(self.ctx)
        await self.ctx.roulette_service.choose(pressed.machine, self.user_id, amount=pressed.amount)


class SpinHandler(RoulettePressHandler[AppContext[DataMessageCallbackQuery]]):
    payload = SpinPress.filter()
    query = payload & HasMessageCallbackQuery()

    async def press(self) -> None:
        await self.ctx.roulette_service.spin(self.payload.parse(self.ctx).machine, self.user_id)


class HintHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    payload = HintPress.filter()
    query = payload & HasMessageCallbackQuery()

    async def handle(self) -> None:
        color = self.payload.parse(self.ctx).color
        hint = ROULETTE.color_hint() if color else ROULETTE.amount_hint()
        await self.ctx.callback_query.answer(self.ctx.text(hint))
