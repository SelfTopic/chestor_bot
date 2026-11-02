from selfrot import MessageHandler
from selfrot.filter import Command, HasUser, Text

from src.bot.dialogs import Dialogs
from src.bot.dialogs.vocab import RACE_NAMES
from src.bot.utils import format_amount

from ....context import AppContext
from ...types import UserMessage


class RaceProfileHandler(MessageHandler[AppContext[UserMessage]]):
    query = (
        Text("распрофиль", ignore_case=True)
        | Text("race profile", ignore_case=True)
        | Command("race_profile")
    ) & HasUser()

    async def handle(self) -> None:
        user = await self.ctx.db_user()

        race = self.ctx.user_service.race(user.race_bit)
        if not race:
            raise RuntimeError(f"Unknown race bit: {user.race_bit}")

        balance = await self.ctx.user_service.balance(user.telegram_id)
        name = await self.ctx.name(user.telegram_id, user.full_name)
        await self.ctx.say(
            Dialogs.profile.card(
                name=name, race=RACE_NAMES[race], balance=format_amount(balance)
            )
        )
