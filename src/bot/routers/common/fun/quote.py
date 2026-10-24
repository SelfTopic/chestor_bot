from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import Command

from src.bot.dialogs import Dialogs

from ....context import AppContext
from ...types import TextMessage


class QuoteArgs(CommandArgs):
    who: Rest = ""


class QuoteHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("цитата", QuoteArgs, prefixes="", ignore_case=True)
    query = cmd

    async def handle(self) -> None:
        who = self.cmd.parse(self.ctx).who.strip()
        quote = self.ctx.quote_service.random_quote(who)
        if quote is None:
            await self.ctx.say(Dialogs.fun.quote.not_found(), reply=True)
            return

        await self.ctx.say(
            Dialogs.fun.quote.result(character=quote.character_name, text=quote.text),
            reply=True,
        )
