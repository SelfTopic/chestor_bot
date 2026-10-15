from selfrot import (
    BaseRouter,
    CallbackPayload,
    CommandArgs,
    InlineKeyboard,
    MessageHandler,
    Rest,
    button,
)
from selfrot.filter import Command, HasMessageCallbackQuery
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import InlineKeyboardMarkup, InputRichMessage, Message

from src.bot.dialogs import Dialogs
from src.bot.services.notify import post_link
from src.bot.services.player_docs import DocPage, DocTopic
from src.config import settings

from ...context import AppContext
from ..types import DataMessageCallbackQuery, TextMessage

# Данные кнопки Telegram ограничивает 64 байтами; слово подсказки — кириллица, по 2 байта.
MAX_SUGGESTION_BYTES = 50


class HelpTopicPress(CallbackPayload, prefix="help"):
    word: str


async def topic_reply(
    ctx: AppContext[object], found: DocTopic | DocPage
) -> tuple[InputRichMessage, InlineKeyboardMarkup | None]:
    channel = settings.DOCS_CHANNEL
    posts = await ctx.player_docs_service.published(channel) if channel else {}
    page = found.page if isinstance(found, DocTopic) else found
    keyboard = None
    if page.slug in posts:
        more = button(ctx.text(Dialogs.help.more()), url=post_link(channel, posts[page.slug]))
        keyboard = InlineKeyboard().row(more).markup()
    return InputRichMessage(markdown=found.markdown), keyboard


class HelpArgs(CommandArgs):
    query: Rest = ""


class HelpHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("help", HelpArgs)
    query = cmd

    async def handle(self) -> None:
        asked = self.cmd.parse(self.ctx).query.strip()
        if not asked:
            await self.sections()
            return

        docs = self.ctx.player_docs_service
        found = docs.find(asked)
        if found is not None:
            rich, keyboard = await topic_reply(self.ctx, found)
            await self.ctx.message.reply_rich_message(rich_message=rich, reply_markup=keyboard)
            return

        suggestions = [
            word for word in docs.suggest(asked) if len(word.encode()) <= MAX_SUGGESTION_BYTES
        ]
        if not suggestions:
            await self.ctx.say(Dialogs.help.not_found(query=asked), reply=True)
            return
        keyboard = InlineKeyboard()
        for word in suggestions:
            keyboard.row(button(word, HelpTopicPress(word=word)))
        await self.ctx.message.reply(
            self.ctx.text(Dialogs.help.did_you_mean(query=asked)), reply_markup=keyboard.markup()
        )

    async def sections(self) -> None:
        channel = settings.DOCS_CHANNEL
        docs = self.ctx.player_docs_service
        posts = await docs.published(channel) if channel else {}
        rows = "\n".join(
            f"- [{page.title}]({post_link(channel, posts[page.slug])})"
            if page.slug in posts
            else f"- {page.title}"
            for page in docs.pages()
        )
        markdown = self.ctx.text(Dialogs.help.sections(rows=rows))
        await self.ctx.message.reply_rich_message(rich_message=InputRichMessage(markdown=markdown))


class HelpTopicPressHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    press = HelpTopicPress.filter()
    query = press & HasMessageCallbackQuery()

    async def handle(self) -> None:
        callback = self.ctx.callback_query
        found = self.ctx.player_docs_service.find(self.press.parse(self.ctx).word)
        message = callback.message
        if found is None or not isinstance(message, Message):
            await callback.answer(self.ctx.text(Dialogs.errors.cannot_process()))
            return
        rich, keyboard = await topic_reply(self.ctx, found)
        await message.edit_text(rich_message=rich, reply_markup=keyboard)
        await callback.answer()


class HelpRouter(BaseRouter[AppContext]):
    handlers = (HelpHandler, HelpTopicPressHandler)
