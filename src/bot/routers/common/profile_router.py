from selfrot import BaseRouter, MessageHandler
from selfrot.filter import Command, HasUser, Text

from src.bot.dialogs import Dialogs
from src.bot.dialogs.vocab import RACE_NAMES
from src.bot.utils import format_amount

from ...context import AppContext
from ..types import UserMessage


class ProfileHandler(MessageHandler[AppContext[UserMessage]]):
    query = (
        Text("профиль", ignore_case=True)
        | Text("profile", ignore_case=True)
        | Command("profile")
    ) & HasUser()

    async def handle(self) -> None:
        user = await self.ctx.db_user()

        race = self.ctx.user_service.race(user.race_bit)

        race_name = Dialogs.profile.unknown_race() if not race else RACE_NAMES[race]

        balance = await self.ctx.user_service.balance(user.telegram_id)
        name = await self.ctx.name(user.telegram_id, user.full_name)
        await self.ctx.say(
            Dialogs.profile.card(
                name=name, race=race_name, balance=format_amount(balance)
            )
        )


class ProfileRouter(BaseRouter[AppContext]):
    handlers = (ProfileHandler,)
