from selfrot import BaseRouter, CommandArgs, InlineKeyboard, MessageHandler, Rest, button
from selfrot.filter import Command
from selfrot.types import InputRichMessage

from src.bot.dialogs import Dialogs
from src.bot.services.notify import post_link
from src.bot.services.player_docs import DocTopic
from src.config import settings

from ...context import AppContext
from ..types import TextMessage


class HelpArgs(CommandArgs):
    query: Rest = ""


class HelpHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("help", HelpArgs)
    query = cmd

    async def handle(self) -> None:
        docs = self.ctx.player_docs_service
        channel = settings.DOCS_CHANNEL
        posts = await docs.published(channel) if channel else {}
        asked = self.cmd.parse(self.ctx).query.strip()
        if not asked:
            await self.sections(posts)
            return

        found = docs.find(asked)
        if found is None:
            await self.ctx.say(Dialogs.help.not_found(query=asked), reply=True)
            return

        page = found.page if isinstance(found, DocTopic) else found
        keyboard = None
        if page.slug in posts:
            more = button(self.ctx.text(Dialogs.help.more()), url=post_link(channel, posts[page.slug]))
            keyboard = InlineKeyboard().row(more).markup()
        await self.ctx.message.reply_rich_message(
            rich_message=InputRichMessage(markdown=found.markdown), reply_markup=keyboard
        )

    async def sections(self, posts: dict[str, int]) -> None:
        channel = settings.DOCS_CHANNEL
        rows = "\n".join(
            f"- [{page.title}]({post_link(channel, posts[page.slug])})"
            if page.slug in posts
            else f"- {page.title}"
            for page in self.ctx.player_docs_service.pages()
        )
        markdown = self.ctx.text(Dialogs.help.sections(rows=rows))
        await self.ctx.message.reply_rich_message(
            rich_message=InputRichMessage(markdown=markdown)
        )


class HelpRouter(BaseRouter[AppContext]):
    handlers = (HelpHandler,)
