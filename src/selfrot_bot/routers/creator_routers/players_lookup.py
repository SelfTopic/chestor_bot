from selfrot import BaseRouter, CommandArgs, MessageHandler
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from ...context import AppContext
from ..types import TextMessage


class AdminProfileArgs(CommandArgs):
    target: str


class AdminProfileHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("admin_profile", AdminProfileArgs)
    query = cmd
    usage = "Использование: /admin_profile <telegram_id или @username>"

    async def handle(self) -> None:
        target = self.cmd.parse(self.ctx).target

        profile = await self.ctx.player_lookup_service.get_profile(target)
        if not profile:
            await self.ctx.message.answer("❌ Пользователь не найден.")
            return

        await self.ctx.message.answer(
            self.ctx.player_lookup_service.format_profile(profile), parse_mode="HTML"
        )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.usage)
            return

        raise exc


class PlayersLookupRouter(BaseRouter[AppContext]):
    handlers = (AdminProfileHandler,)
