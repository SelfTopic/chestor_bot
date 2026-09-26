from typing import Any

from selfrot import BaseContext
from selfrot.filter import BaseFilter

from ....context import AppContext


class NeedsRegistrationOrRebirth(BaseFilter[AppContext[Any]]):
    async def check(self, ctx: BaseContext[Any]) -> bool:
        assert isinstance(ctx, AppContext)

        user = ctx.user
        if user is None:
            return False

        ghoul = await ctx.ghoul_service.get(find_by=user.id)
        return ghoul is None or ghoul.is_dead
