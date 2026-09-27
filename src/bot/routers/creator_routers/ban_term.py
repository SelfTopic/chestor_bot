from datetime import datetime
from typing import Any

from src.bot.dialogs import Dialogs

from ...context import AppContext


def ban_term(ctx: AppContext[Any], banned_until: datetime | None) -> str:
    if banned_until is None:
        return ctx.text(Dialogs.banned.forever())
    date = banned_until.strftime("%d.%m.%Y %H:%M")
    return ctx.text(Dialogs.banned.until(date=date))
