import html
import random
import re
from typing import Annotated, TypeVar

from pydantic import Field
from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import AnyCommand, Command

from ....context import AppContext
from ...types import TextMessage
from .filters import Arithmetic

TArgs = TypeVar("TArgs", bound=CommandArgs)

ITEM_SEPARATOR = re.compile(r"\s*(?:,|\bили\b)\s*", re.IGNORECASE)
MAX_PICK_ITEMS = 50
MAX_ITEM_LENGTH = 200
NOBODY = "Пока некого выбирать - в этом чате ещё никто не написал боту."


def bot_command(action: str, args: type[TArgs]) -> AnyCommand[TArgs]:
    return AnyCommand(
        *(
            Command(f"{name} {action}", args, prefixes="", ignore_case=True, strict=True)
            for name in ("бот", "честор")
        )
    )


async def random_mention(ctx: AppContext[TextMessage]) -> str | None:
    user = await ctx.chat_service.random_participant(ctx.message.chat.id)
    if user is None:
        return None
    return f'<a href="tg://user?id={user.telegram_id}">{html.escape(user.full_name)}</a>'


class PickArgs(CommandArgs):
    items: Rest


class PickHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = bot_command("выбери", PickArgs)
    query = cmd
    too_few = "Нужно минимум 2 варианта: бот выбери пицца или суши или бургер"
    too_many = f"Слишком много вариантов (максимум {MAX_PICK_ITEMS})."
    too_long = "Один из вариантов слишком длинный."

    async def handle(self) -> None:
        text = self.cmd.parse(self.ctx).items
        items = [item.strip() for item in ITEM_SEPARATOR.split(text) if item.strip()]
        message = self.ctx.message

        if len(items) < 2:
            await message.reply(self.too_few)
        elif len(items) > MAX_PICK_ITEMS:
            await message.reply(self.too_many)
        elif any(len(item) > MAX_ITEM_LENGTH for item in items):
            await message.reply(self.too_long)
        else:
            await message.reply(f"🎲 Выбор пал на: {random.choice(items)}")


class WhoArgs(CommandArgs):
    question: Rest


class WhoHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = bot_command("кто", WhoArgs)
    query = cmd

    async def handle(self) -> None:
        question = self.cmd.parse(self.ctx).question
        message = self.ctx.message

        mention = await random_mention(self.ctx)
        if mention is None:
            await message.reply(NOBODY)
            return

        await message.reply(
            f"По моим расчётам {html.escape(question)} {mention}", parse_mode="HTML"
        )


class RandomParticipantHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = AnyCommand(
        *(
            Command(f"{name} случайный участник", prefixes="", ignore_case=True, args_count=0)
            for name in ("бот", "честор")
        )
    )
    query = cmd

    async def handle(self) -> None:
        mention = await random_mention(self.ctx)
        if mention is None:
            await self.ctx.message.reply(NOBODY)
            return

        await self.ctx.message.reply(f"🎲 Выбор пал на {mention}!", parse_mode="HTML")


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
        await self.ctx.message.reply(f"🎲 {random.randint(low, high)}")


class CalculatorHandler(MessageHandler[AppContext[TextMessage]]):
    arithmetic = Arithmetic()
    query = arithmetic

    async def handle(self) -> None:
        result = self.arithmetic.result(self.ctx)
        assert result is not None
        await self.ctx.message.reply(result)
