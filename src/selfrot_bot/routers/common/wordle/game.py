import logging

from selfrot import MessageHandler
from selfrot.exceptions import TelegramBadRequest
from selfrot.filter import TextRegexp
from selfrot.types import InputFile

from src.bot.game_configs import WORDLE_CONFIG
from src.bot.types.wordle import WordleGuessResult

from ....context import AppContext
from ....types import TextUserMessage
from .captions import guess_caption, lose_text, win_text
from .filters import HasActiveWordleGame

logger = logging.getLogger(__name__)


class WordleGameHandler(MessageHandler[AppContext[TextUserMessage]]):
    # одно слово из пяти символов от игрока с незавершённой партией: у прода это был
    # один самописный фильтр, теперь готовый TextRegexp плюс проверка партии
    query = TextRegexp(r"\s*\S{5}\s*", full=True) & HasActiveWordleGame()

    async def delete_board(self, message_id: int) -> None:
        """Удалить старую доску; не вышло, так не вышло: партия от этого не страдает."""
        try:
            await self.ctx.bot.delete_message(
                chat_id=self.ctx.message.chat.id, message_id=message_id
            )
        except Exception:
            logger.debug("Failed to delete board message %d", message_id)

    async def notify_finish(self, result: WordleGuessResult) -> None:
        """Финальное уведомление о победе или поражении."""
        if not (result.is_won or result.is_lost):
            return

        summary = await self.ctx.wikipedia_service.get_summary(result.target)

        if result.is_won:
            award = WORDLE_CONFIG.award
            await self.ctx.user_service.plus_balance(
                telegram_id=self.ctx.message.user.id,
                change_balance=award,
                log="wordle win",
            )
            text = win_text(result, award, summary)
        else:
            text = lose_text(result, summary)

        await self.ctx.message.answer(text, parse_mode="HTML")

    async def handle(self) -> None:
        message = self.ctx.message
        wordle_service = self.ctx.wordle_service

        user_id = message.user.id
        word = message.text.strip()

        result = wordle_service.guess(telegram_id=user_id, word=word)
        if not result:
            return

        if result.board_message_id:
            await self.delete_board(result.board_message_id)

        try:
            await message.delete()

        except TelegramBadRequest:
            pass

        sent = await message.answer_photo(
            photo=InputFile(result.png, "wordle.png"),
            caption=guess_caption(result, word),
            parse_mode="HTML",
        )
        wordle_service.set_board_message_id(user_id, sent.message_id)
        await self.notify_finish(result)
