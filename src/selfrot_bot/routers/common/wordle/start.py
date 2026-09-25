from selfrot import MessageHandler
from selfrot.filter import Command, HasUser, Text
from selfrot.types import InputFile

from ....context import AppContext
from ....types import UserMessage


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
                caption=(
                    "У вас есть незавершённая игра.\n"
                    "Введите слово из 5 букв чтобы продолжить."
                ),
            )
            wordle_service.set_board_message_id(user_id, sent.message_id)
            return

        photo = wordle_service.start_new_game(telegram_id=user_id)
        sent = await message.reply_photo(
            photo=InputFile(photo, "wordle.png"),
            caption=(
                "🟩 <b>Новая игра!</b>\n\n"
                "Угадайте слово из 5 букв за 6 попыток.\n"
                "🟩 — буква на своём месте\n"
                "🟨 — буква есть, но не там\n"
                "⬛ — буквы нет в слове"
            ),
            parse_mode="HTML",
        )
        wordle_service.set_board_message_id(user_id, sent.message_id)
