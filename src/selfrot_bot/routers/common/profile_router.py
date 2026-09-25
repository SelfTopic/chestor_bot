from selfrot import BaseRouter, MessageHandler
from selfrot.filter import Command, HasUser, Text

from ...context import AppContext
from ...types import UserMessage


class ProfileHandler(MessageHandler[AppContext[UserMessage]]):
    # два триггера у одного хендлера: в aiogram это два декоратора, здесь `|`
    query = (Text("профиль", ignore_case=True) | Command("profile")) & HasUser()

    async def handle(self) -> None:
        user = await self.ctx.db_user()

        race = self.ctx.user_service.race(user.race_bit)

        race_name = (
            "Ээээ.. Пока неясно что это такое." if not race else race.value["name"]
        )

        await self.ctx.answer_message(
            self.ctx.dialog_service.text(
                key="profile",
                name=user.full_name,
                race=race_name,
                balance=str(user.balance),
            )
        )


class ProfileRouter(BaseRouter[AppContext]):
    handlers = (ProfileHandler,)
