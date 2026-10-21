import html
import random
import re
from typing import Annotated

from pydantic import Field
from selfrot import CommandArgs, MessageHandler, Rest, mention_html
from selfrot.filter import AnyCommand, Command

from src.bot.dialogs import Dialogs

from ....context import AppContext
from ...types import TextMessage
from .calculator import DivisionByZero, ResultTooBig
from ...bot_command import bot_command
from .filters import Arithmetic

ITEM_SEPARATOR = re.compile(r"\s*(?:,|\bили\b)\s*", re.IGNORECASE)
MAX_PICK_ITEMS = 50
MAX_ITEM_LENGTH = 200
NOBODY = Dialogs.fun.nobody()


class PickArgs(CommandArgs):
    items: Rest


class WhoArgs(CommandArgs):
    question: Rest


Integer = Annotated[str, Field(pattern=r"^-?\d+$")]


class NumberArgs(CommandArgs):
    low: Integer
    high: Integer


class AskBotHandler(MessageHandler[AppContext[TextMessage]]):
    pick_cmd = bot_command("выбери", PickArgs)
    who_cmd = bot_command("кто", WhoArgs)
    participant_cmd = AnyCommand(
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
    number_cmd = bot_command("число", NumberArgs)

    too_few = Dialogs.fun.pick.too_few()
    too_many = Dialogs.fun.pick.too_many(max_items=MAX_PICK_ITEMS)
    too_long = Dialogs.fun.pick.too_long()

    @pick_cmd
    async def pick(self) -> None:
        text = self.pick_cmd.parse(self.ctx).items
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

    @who_cmd
    async def who(self) -> None:
        question = self.who_cmd.parse(self.ctx).question

        mention = await self.random_mention()
        if mention is None:
            await self.ctx.say(NOBODY, reply=True)
            return

        await self.ctx.say(
            Dialogs.fun.who(question=html.escape(question), mention=mention),
            reply=True,
            parse_mode="HTML",
        )

    @participant_cmd
    async def participant(self) -> None:
        mention = await self.random_mention()
        if mention is None:
            await self.ctx.say(NOBODY, reply=True)
            return

        await self.ctx.say(
            Dialogs.fun.random_participant(mention=mention),
            reply=True,
            parse_mode="HTML",
        )

    @number_cmd
    async def number(self) -> None:
        args = self.number_cmd.parse(self.ctx)
        low, high = sorted((int(args.low), int(args.high)))
        number = random.randint(low, high)
        await self.ctx.say(Dialogs.fun.number(number=number), reply=True)

    async def random_mention(self) -> str | None:
        user = await self.ctx.chat_service.random_participant(self.ctx.message.chat.id)
        if user is None:
            return None
        return mention_html(user.telegram_id, user.full_name)


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
