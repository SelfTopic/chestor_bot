import logging
from collections.abc import Callable

from selfrot.exceptions import TelegramAPIError
from selfrot.types import (
    InputRichBlockParagraph,
    InputRichMessage,
    Message,
    RichBlockTableCell,
)

logger = logging.getLogger(__name__)


def paragraph(text: str) -> InputRichBlockParagraph:
    return InputRichBlockParagraph(text=text)


def table_cell(text: str, *, header: bool = False) -> RichBlockTableCell:
    return RichBlockTableCell(
        align="center", valign="middle", text=text, is_header=header or None
    )


async def answer_rich_or_text(
    message: Message,
    rich_message: InputRichMessage,
    fallback: Callable[[], str],
    *,
    what: str,
) -> None:
    """
    Rich-сообщение (Bot API 10.1+). Свежая фича: на клиенте или в чате, который её не
    поддерживает, Telegram отвечает ошибкой, и тогда уходит обычный текст. Текст
    строится только если он нужен (fallback вызывается по требованию).
    """
    try:
        await message.answer_rich_message(rich_message=rich_message)
    except TelegramAPIError:
        logger.warning(
            "send_rich_message failed for %s, falling back to plain text",
            what,
            exc_info=True,
        )
        await message.answer(fallback())
