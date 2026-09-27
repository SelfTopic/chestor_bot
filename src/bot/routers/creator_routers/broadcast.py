from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from src.bot.dialogs import Dialogs
from src.bot.exceptions import UserNotFound

from ...context import AppContext
from ..types import TextMessage


class BroadcastTextArgs(CommandArgs):
    text: Rest


class BroadcastPrivateHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("broadcast_private", BroadcastTextArgs)
    query = cmd
    usage = Dialogs.admin.broadcast.private_usage()

    async def handle(self) -> None:
        text = self.cmd.parse(self.ctx).text

        await self.ctx.say(Dialogs.admin.broadcast.started())
        result = await self.ctx.broadcast_service.broadcast_to_private(text)
        finished = Dialogs.admin.broadcast.finished(
            total=result.total, success=result.success, failed=result.failed
        )
        await self.ctx.say(finished)

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.say(self.usage, reply=True)
            return

        raise exc


class BroadcastChatsHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("broadcast_chats", BroadcastTextArgs)
    query = cmd
    usage = Dialogs.admin.broadcast.chats_usage()

    async def handle(self) -> None:
        text = self.cmd.parse(self.ctx).text

        await self.ctx.say(Dialogs.admin.broadcast.started())
        result = await self.ctx.broadcast_service.broadcast_to_chats(text)
        finished = Dialogs.admin.broadcast.finished(
            total=result.total, success=result.success, failed=result.failed
        )
        await self.ctx.say(finished)

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.say(self.usage, reply=True)
            return

        raise exc


class BroadcastAllHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("broadcast_all", BroadcastTextArgs)
    query = cmd
    usage = Dialogs.admin.broadcast.all_usage()

    async def handle(self) -> None:
        text = self.cmd.parse(self.ctx).text

        await self.ctx.say(Dialogs.admin.broadcast.started())
        result = await self.ctx.broadcast_service.broadcast_to_all(text)
        finished = Dialogs.admin.broadcast.finished(
            total=result.total, success=result.success, failed=result.failed
        )
        await self.ctx.say(finished)

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.say(self.usage, reply=True)
            return

        raise exc


class BroadcastUserArgs(CommandArgs):
    target: str
    text: Rest


class BroadcastUserHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("broadcast_user", BroadcastUserArgs)
    query = cmd
    usage = Dialogs.admin.broadcast.user_usage()

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)

        try:
            ok = await self.ctx.broadcast_service.send_to_target(args.target, args.text)
        except UserNotFound as e:
            await self.ctx.say(Dialogs.errors.user_not_found(query=e.query))
            return

        broadcast = Dialogs.admin.broadcast
        await self.ctx.say(broadcast.sent() if ok else broadcast.blocked())

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.say(self.usage, reply=True)
            return

        raise exc


class BroadcastRouter(BaseRouter[AppContext]):
    handlers = (
        BroadcastPrivateHandler,
        BroadcastChatsHandler,
        BroadcastAllHandler,
        BroadcastUserHandler,
    )
