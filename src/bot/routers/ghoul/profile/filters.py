from typing import Any

from selfrot import BaseContext
from selfrot.filter import BaseFilter

from src.bot.types import Race

from ....context import AppContext


class GhoulRace(BaseFilter[AppContext[Any]]):
    async def check(self, ctx: BaseContext[Any]) -> bool:
        assert isinstance(ctx, AppContext)

        sender = ctx.user
        if sender is None:
            return False

        user = await ctx.user_service.get(sender.id)
        return user is not None and ctx.user_service.race(user.race_bit) == Race.GHOUL
