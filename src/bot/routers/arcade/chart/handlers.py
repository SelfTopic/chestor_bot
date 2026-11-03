from typing import Generic, TypeVar

from selfrot import MessageHandler
from selfrot.filter import Command, HasMessageCallbackQuery, HasUser, Text
from selfrot.handlers import CallbackQueryHandler

from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import (
    ChartAlreadyBet,
    ChartAlreadyCashedOut,
    ChartBetOutOfRange,
    ChartBetsClosed,
    ChartMachineOpen,
    ChartNoBet,
    ChartNoMachine,
    ChartNotEnoughMoney,
    ChartNotGrowing,
    ChartTooLate,
    ChartUnavailable,
)
from src.bot.utils import format_amount

from ....context import AppContext
from ...types import DataMessageCallbackQuery, TextUserMessage
from .payloads import BetPress, CashOutPress, HintPress, TargetPress
from .screen import multiplier

CHART = Dialogs.chart
TContext = TypeVar("TContext", bound=AppContext[DataMessageCallbackQuery])


class OpenChartHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = (
        Text("джет", ignore_case=True) | Text("jet", ignore_case=True) | Command("jet")
    ) & HasUser()

    async def handle(self) -> None:
        message = self.ctx.message
        await self.ctx.chart_service.open(message.chat.id, message.user.id)

    def machine_link(self, message_id: int) -> str | None:
        chat = self.ctx.message.chat
        if chat.username:
            return f"https://t.me/{chat.username}/{message_id}"
        # У приватной супергруппы id вида -100…: ссылка t.me/c/ берёт его без -100.
        if chat.type == "supergroup" and str(chat.id).startswith("-100"):
            return f"https://t.me/c/{str(chat.id)[4:]}/{message_id}"
        return None

    async def on_error(self, exc: Exception) -> None:
        match exc:
            case ChartMachineOpen(message_id=int(message_id)) if (
                link := self.machine_link(message_id)
            ):
                await self.ctx.say(CHART.already_open_link(link=link), reply=True, parse_mode="HTML")
            case ChartMachineOpen():
                await self.ctx.say(CHART.already_open(), reply=True)
            case ChartUnavailable():
                await self.ctx.say(CHART.unavailable(), reply=True)
            case _:
                raise exc


# Нажатие сообщение не правит (две правки на раунд): итог — всплывашкой.
class ChartPressHandler(CallbackQueryHandler[TContext], Generic[TContext]):
    no_bet: Line = CHART.no_bet()

    @property
    def chat_id(self) -> int:
        return self.ctx.callback_query.message.chat.id

    @property
    def user_id(self) -> int:
        return self.ctx.callback_query.user.id

    async def answer(self, line: Line) -> None:
        await self.ctx.callback_query.answer(self.ctx.text(line))

    async def handle(self) -> None:
        await self.answer(await self.press())

    async def press(self) -> Line:
        raise NotImplementedError

    def error_line(self, exc: Exception) -> Line | None:
        match exc:
            case ChartNoMachine():
                return CHART.machine_closed()
            case ChartBetsClosed():
                return CHART.bets_closed()
            case ChartAlreadyBet():
                return CHART.already_bet()
            case ChartBetOutOfRange(min_bet=min_bet, max_bet=max_bet):
                return CHART.bet_out_of_range(
                    min_bet=format_amount(min_bet), max_bet=format_amount(max_bet)
                )
            case ChartNotEnoughMoney():
                return CHART.not_enough_money()
            case ChartNoBet():
                return self.no_bet
            case ChartNotGrowing():
                return CHART.not_growing()
            case ChartAlreadyCashedOut(multiplier=cashed_at):
                return CHART.already_cashed(multiplier=multiplier(cashed_at))
            case ChartTooLate(crash=crash):
                return CHART.too_late(crash=multiplier(crash))
            case _:
                return None

    async def on_error(self, exc: Exception) -> None:
        line = self.error_line(exc)
        if line is None:
            raise exc
        await self.answer(line)


class BetHandler(ChartPressHandler[AppContext[DataMessageCallbackQuery]]):
    payload = BetPress.filter()
    query = payload & HasMessageCallbackQuery()

    async def press(self) -> Line:
        amount = self.payload.parse(self.ctx).amount
        await self.ctx.chart_service.bet(self.chat_id, self.user_id, amount, None)
        return CHART.bet_placed(amount=format_amount(amount))


class TargetHandler(ChartPressHandler[AppContext[DataMessageCallbackQuery]]):
    payload = TargetPress.filter()
    query = payload & HasMessageCallbackQuery()
    no_bet = CHART.no_bet_for_target()

    async def press(self) -> Line:
        target = self.payload.parse(self.ctx).target
        await self.ctx.chart_service.set_target(self.chat_id, self.user_id, target)
        return CHART.target_set(target=f"{target / 100:g}")


class CashOutHandler(ChartPressHandler[AppContext[DataMessageCallbackQuery]]):
    query = CashOutPress.filter() & HasMessageCallbackQuery()

    async def press(self) -> Line:
        bet = await self.ctx.chart_service.cash_out(self.chat_id, self.user_id)
        assert bet.cashed_at is not None
        return CHART.cashed(multiplier=multiplier(bet.cashed_at), payout=format_amount(bet.payout))


class HintHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    payload = HintPress.filter()
    query = payload & HasMessageCallbackQuery()

    async def handle(self) -> None:
        hint = CHART.target_hint() if self.payload.parse(self.ctx).target else CHART.bet_hint()
        await self.ctx.callback_query.answer(self.ctx.text(hint))
