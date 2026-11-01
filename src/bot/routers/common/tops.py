from datetime import timedelta
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field
from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import AnyCommand, Command, HasUser

from src.bot.dialogs import Dialogs, Line
from src.bot.utils import format_amount

from ...context import AppContext
from ...repositories import TopWallet
from ..tops import chat_scoped, is_group, wants_chat, you_line
from ..types import TextUserMessage


class TopArgs(CommandArgs):
    count: int = Field(20, ge=1, le=50)
    extra: Rest = ""


class TopBalanceHandler(MessageHandler[AppContext[TextUserMessage]]):
    cmd = chat_scoped(("топ бал", "top bal"), TopArgs)
    query = cmd & HasUser()
    range_error = Dialogs.tops.balance.bad_count()
    chat_only_group = Dialogs.tops.chat_only_group()

    async def handle(self) -> None:
        count = self.cmd.parse(self.ctx).count
        chat = self.ctx.message.chat
        local = wants_chat(self.cmd, self.ctx)
        if local and not is_group(chat.type):
            await self.ctx.say(self.chat_only_group, reply=True)
            return

        chat_id = chat.id if local else None
        top = await self.ctx.user_service.get_top_balance(count, chat_id)

        rows = "\n".join(
            self.ctx.text(
                Dialogs.tops.balance.row(
                    place=place,
                    name=self.wallet_name(wallet),
                    balance=format_amount(wallet.balance),
                )
            )
            for place, wallet in enumerate(top, start=1)
        )
        me = self.ctx.message.user.id
        place = await self.ctx.user_service.balance_place(me, chat_id)
        balance = await self.ctx.user_service.balance(me)
        you = you_line(self.ctx, place, format_amount(balance or 0))
        message = Dialogs.tops.balance.chat_message if local else Dialogs.tops.balance.message
        await self.ctx.say(message(count=count, rows=rows, you=you))

    def wallet_name(self, wallet: TopWallet) -> str:
        if not wallet.is_family:
            return wallet.names[0]
        if wallet.family_name:
            return wallet.family_name
        return self.ctx.text(Dialogs.family.top_name(members=", ".join(wallet.names)))

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.say(self.range_error, reply=True)
            return

        raise exc


MESSAGE_TOP_SIZE = 20
Period = Literal["day", "week", "month"]
PERIOD_WORDS: dict[str, Period] = {
    "день": "day",
    "неделя": "week",
    "месяц": "month",
    "day": "day",
    "week": "week",
    "month": "month",
}
WINDOWS: dict[Period, timedelta] = {
    "day": timedelta(days=1),
    "week": timedelta(days=7),
    "month": timedelta(days=30),
}
MESSAGE_TOTALS = {
    None: Dialogs.tops.messages.total_all,
    "day": Dialogs.tops.messages.total_day,
    "week": Dialogs.tops.messages.total_week,
    "month": Dialogs.tops.messages.total_month,
}
MESSAGE_TITLES: dict[Period | None, Line] = {
    None: Dialogs.tops.messages.title_all(),
    "day": Dialogs.tops.messages.title_day(),
    "week": Dialogs.tops.messages.title_week(),
    "month": Dialogs.tops.messages.title_month(),
}


def period_of(word: object) -> object:
    return PERIOD_WORDS.get(word.lower(), word) if isinstance(word, str) else word


class MessageTopArgs(CommandArgs):
    period: Annotated[Period | None, BeforeValidator(period_of)] = None


class MessageTopHandler(MessageHandler[AppContext[TextUserMessage]]):
    # strict: «топ бал» и прочие топы с чужим словом после «топ» не про сообщения.
    cmd = AnyCommand(
        *(
            Command(word, MessageTopArgs, prefixes="", ignore_case=True, strict=True)
            for word in ("топ", "стата", "top", "stats")
        )
    )
    query = cmd & HasUser()
    only_group = Dialogs.tops.messages.only_group()
    empty = Dialogs.tops.messages.empty()

    async def handle(self) -> None:
        chat = self.ctx.message.chat
        if not is_group(chat.type):
            await self.ctx.say(self.only_group, reply=True)
            return

        period = self.cmd.parse(self.ctx).period
        window = WINDOWS[period] if period is not None else None
        top = await self.ctx.chat_service.top_messages(chat.id, window, MESSAGE_TOP_SIZE)
        if not top:
            await self.ctx.say(self.empty)
            return

        rows = "\n".join(
            self.ctx.text(
                Dialogs.tops.messages.row(place=place, name=row.first_name, messages=row.messages)
            )
            for place, row in enumerate(top, start=1)
        )
        title = self.ctx.text(MESSAGE_TITLES[period])
        total = await self.ctx.chat_service.total_messages(chat.id, window)
        mine = await self.ctx.chat_service.message_place(chat.id, window, self.ctx.message.user.id)
        place, messages = mine if mine is not None else (None, 0)
        line = Dialogs.tops.messages.message(
            title=title,
            rows=rows,
            total=self.ctx.text(MESSAGE_TOTALS[period](count=total)),
            you=you_line(self.ctx, place, messages),
        )
        await self.ctx.say(line)


class CommonTopsRouter(BaseRouter[AppContext]):
    handlers = (TopBalanceHandler, MessageTopHandler)
