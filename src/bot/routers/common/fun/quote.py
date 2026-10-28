from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import AnyCommand, Command
from selfrot.types import InputRichMessage

from src.bot.dialogs import Dialogs
from src.bot.services.quotes import Quote

from ....context import AppContext
from ...language import RUSSIAN_ONLY, NotInLanguageReply
from ...types import TextMessage

SOURCE_LABEL = {"anime": "Аниме", "comics": "Манга"}


def quote_markdown(quote: Quote) -> str:
    label = SOURCE_LABEL.get(quote.source, quote.source)
    if quote.season is not None and quote.series is not None:
        label += f", {quote.season} сезон, {quote.series} серия"

    return f"# {quote.character_name}\n\n## {quote.text}\n\n_{label}_"


class QuoteArgs(CommandArgs):
    who: Rest = ""


QUOTE = AnyCommand(
    Command("цитата", QuoteArgs, prefixes="", ignore_case=True),
    Command("quote", QuoteArgs, prefixes="", ignore_case=True),
)


class QuoteHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = QUOTE
    query = cmd & RUSSIAN_ONLY

    async def handle(self) -> None:
        who = self.cmd.parse(self.ctx).who.strip()
        quote = self.ctx.quote_service.random_quote(who)
        if quote is None:
            await self.ctx.say(Dialogs.fun.quote.not_found(), reply=True)
            return

        await self.ctx.message.reply_rich_message(
            rich_message=InputRichMessage(markdown=quote_markdown(quote))
        )


class QuoteNotInLanguageHandler(NotInLanguageReply, MessageHandler[AppContext[TextMessage]]):
    query = QUOTE & ~RUSSIAN_ONLY
    line = Dialogs.not_in_language.quote()
