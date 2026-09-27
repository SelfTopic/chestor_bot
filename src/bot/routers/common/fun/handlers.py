import html
import random
import re
from typing import Annotated, TypeVar

from pydantic import Field
from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import AnyCommand, Command

from src.bot.dialogs import Dialogs

from ....context import AppContext
from ...types import TextMessage
from .calculator import DivisionByZero, ResultTooBig
from .filters import Arithmetic

TArgs = TypeVar("TArgs", bound=CommandArgs)

ITEM_SEPARATOR = re.compile(r"\s*(?:,|\bили\b)\s*", re.IGNORECASE)
MAX_PICK_ITEMS = 50
MAX_ITEM_LENGTH = 200
NOBODY = Dialogs.fun.nobody()


def bot_command(action: str, args: type[TArgs]) -> AnyCommand[TArgs]:
    return AnyCommand(
        *(
            Command(
                f"{name} {action}", args, prefixes="", ignore_case=True, strict=True
            )
            for name in ("бот", "честор")
        )
    )


async def random_mention(ctx: AppContext[TextMessage]) -> str | None:
    user = await ctx.chat_service.random_participant(ctx.message.chat.id)
    if user is None:
        return None
    return (
        f'<a href="tg://user?id={user.telegram_id}">{html.escape(user.full_name)}</a>'
    )


class PickArgs(CommandArgs):
    items: Rest


class PickHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = bot_command("выбери", PickArgs)
    query = cmd
    too_few = Dialogs.fun.pick.too_few()
    too_many = Dialogs.fun.pick.too_many(max_items=MAX_PICK_ITEMS)
    too_long = Dialogs.fun.pick.too_long()

    async def handle(self) -> None:
        text = self.cmd.parse(self.ctx).items
        items = [item.strip() for item in ITEM_SEPARATOR.split(text) if item.strip()]

        if len(items) < 2:
            line = self.too_few
        elif len(items) > MAX_PICK_ITEMS:
            line = self.too_many
        elif any(len(item) > MAX_ITEM_LENGTH for item in items):
            line = self.too_long
        else:
            line = Dialogs.fun.pick.result(choice=random.choice(items))
        await self.ctx.say(line, reply=True)


class WhoArgs(CommandArgs):
    question: Rest


class WhoHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = bot_command("кто", WhoArgs)
    query = cmd

    async def handle(self) -> None:
        question = self.cmd.parse(self.ctx).question

        mention = await random_mention(self.ctx)
        if mention is None:
            await self.ctx.say(NOBODY, reply=True)
            return

        await self.ctx.say(
            Dialogs.fun.who(question=html.escape(question), mention=mention),
            reply=True,
            parse_mode="HTML",
        )


class RandomParticipantHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = AnyCommand(
        *(
            Command(
                f"{name} случайный участник",
                prefixes="",
                ignore_case=True,
                args_count=0,
            )
            for name in ("бот", "честор")
        )
    )
    query = cmd

    async def handle(self) -> None:
        mention = await random_mention(self.ctx)
        if mention is None:
            await self.ctx.say(NOBODY, reply=True)
            return

        await self.ctx.say(
            Dialogs.fun.random_participant(mention=mention),
            reply=True,
            parse_mode="HTML",
        )


Integer = Annotated[str, Field(pattern=r"^-?\d+$")]


class NumberArgs(CommandArgs):
    low: Integer
    high: Integer


class RandomNumberHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = bot_command("число", NumberArgs)
    query = cmd

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        low, high = sorted((int(args.low), int(args.high)))
        number = random.randint(low, high)
        await self.ctx.say(Dialogs.fun.number(number=number), reply=True)


class CalculatorHandler(MessageHandler[AppContext[TextMessage]]):
    arithmetic = Arithmetic()
    query = arithmetic

    async def handle(self) -> None:
        outcome = self.arithmetic.outcome(self.ctx)
        assert outcome is not None

        if isinstance(outcome, DivisionByZero):
            await self.ctx.say(Dialogs.fun.calculator.division_by_zero(), reply=True)
        elif isinstance(outcome, ResultTooBig):
            await self.ctx.say(Dialogs.fun.calculator.too_big(), reply=True)
        elif isinstance(outcome, float) and outcome.is_integer():
            await self.ctx.message.reply(str(int(outcome)))
        else:
            await self.ctx.message.reply(str(outcome))
