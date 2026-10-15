import logging

from selfrot import BaseRouter, MessageHandler
from selfrot.exceptions import TelegramAPIError, TelegramBadRequest, TelegramNetworkError
from selfrot.filter import Command, HasReplyToMessage, HasUser
from selfrot.types import InputRichMessage

from src.bot.dialogs import Dialogs

from ...context import AppContext
from ..types import TextUserMessage, TextUserReplyToMessage

logger = logging.getLogger(__name__)

RICH = Dialogs.rich
MARKDOWN_SUFFIXES = (".md", ".markdown")
# Лимит rich-сообщения Telegram — 32768 символов; файл больше заведомо не влезет.
MAX_CHARS = 32768
MAX_FILE_BYTES = 4 * MAX_CHARS


class RichHandler(MessageHandler[AppContext[TextUserReplyToMessage]]):
    query = Command("rich", args_count=0) & HasReplyToMessage() & HasUser()

    # Скачивание файла — сеть: в handle держали бы сессию БД.
    file_id = ""

    async def handle(self) -> None:
        document = self.ctx.message.reply_to_message.document
        if document is None or not (document.file_name or "").lower().endswith(MARKDOWN_SUFFIXES):
            await self.ctx.say(RICH.usage(), reply=True)
            return
        if (document.file_size or 0) > MAX_FILE_BYTES:
            await self.ctx.say(RICH.too_long(limit=MAX_CHARS), reply=True)
            return
        self.file_id = document.file_id

    async def after_handle(self) -> None:
        if not self.file_id:
            return
        ctx = self.ctx
        try:
            markdown = (await ctx.bot.download(self.file_id)).decode("utf-8-sig")
        except UnicodeDecodeError:
            await ctx.say(RICH.not_utf8(), reply=True)
            return
        except (TelegramAPIError, TelegramNetworkError):
            logger.warning("/rich: не скачался %s", self.file_id, exc_info=True)
            await ctx.say(RICH.download_failed(), reply=True)
            return

        if not markdown.strip():
            await ctx.say(RICH.empty(), reply=True)
            return
        if len(markdown) > MAX_CHARS:
            await ctx.say(RICH.too_long(limit=MAX_CHARS), reply=True)
            return
        try:
            await ctx.message.reply_rich_message(rich_message=InputRichMessage(markdown=markdown))
        except TelegramBadRequest as error:
            await ctx.say(RICH.rejected(error=str(error)), reply=True)


class RichUsageHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Command("rich") & HasUser()

    async def handle(self) -> None:
        await self.ctx.say(RICH.usage(), reply=True)


class RichRouter(BaseRouter[AppContext]):
    handlers = (RichHandler, RichUsageHandler)
