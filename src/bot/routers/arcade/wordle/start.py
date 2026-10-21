from selfrot import MessageHandler
from selfrot.filter import Command, HasUser, Text
from selfrot.types import InputFile

from src.bot.dialogs import Dialogs

from ....context import AppContext
from ...types import UserMessage


class WordleStartHandler(MessageHandler[AppContext[UserMessage]]):
    query = (
        Text("вордли", ignore_case=True)
        | Text("вротли", ignore_case=True)
        | Command("wordle")
    ) & HasUser()

    async def handle(self) -> None:
        message = self.ctx.message
        wordle_service = self.ctx.wordle_service
        user_id = message.user.id

        photo = wordle_service.get_current_board(telegram_id=user_id)
        if photo:
            sent = await message.reply_photo(
                photo=InputFile(photo, "wordle.png"),
                caption=self.ctx.text(Dialogs.wordle.resume()),
            )
            wordle_service.set_board_message_id(user_id, sent.message_id)
            return

        photo = wordle_service.start_new_game(telegram_id=user_id)
        sent = await message.reply_photo(
            photo=InputFile(photo, "wordle.png"),
            caption=self.ctx.text(Dialogs.wordle.new_game()),
            parse_mode="HTML",
        )
        wordle_service.set_board_message_id(user_id, sent.message_id)
