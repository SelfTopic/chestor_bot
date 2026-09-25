"""/broadcast_private, /broadcast_chats, /broadcast_all, /broadcast_user."""

from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from ...context import AppContext
from ...types import TextMessage


class BroadcastTextArgs(CommandArgs):
    text: Rest


class BroadcastPrivateHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("broadcast_private", BroadcastTextArgs)
    query = cmd
    usage = "Использование: /broadcast_private <текст>"

    async def handle(self) -> None:
        text = self.cmd.parse(self.ctx).text
        message = self.ctx.message

        await message.answer("📤 Рассылка запущена...")
        result = await self.ctx.broadcast_service.broadcast_to_private(text)
        await message.answer(
            f"✅ Рассылка завершена.\n"
            f"Всего: {result.total} | Успешно: {result.success} | Ошибок: {result.failed}"
        )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.usage)
            return

        raise exc


class BroadcastChatsHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("broadcast_chats", BroadcastTextArgs)
    query = cmd
    usage = "Использование: /broadcast_chats <текст>"

    async def handle(self) -> None:
        text = self.cmd.parse(self.ctx).text
        message = self.ctx.message

        await message.answer("📤 Рассылка запущена...")
        result = await self.ctx.broadcast_service.broadcast_to_chats(text)
        await message.answer(
            f"✅ Рассылка завершена.\n"
            f"Всего: {result.total} | Успешно: {result.success} | Ошибок: {result.failed}"
        )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.usage)
            return

        raise exc


class BroadcastAllHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("broadcast_all", BroadcastTextArgs)
    query = cmd
    usage = "Использование: /broadcast_all <текст>"

    async def handle(self) -> None:
        text = self.cmd.parse(self.ctx).text
        message = self.ctx.message

        await message.answer("📤 Рассылка запущена...")
        result = await self.ctx.broadcast_service.broadcast_to_all(text)
        await message.answer(
            f"✅ Рассылка завершена.\n"
            f"Всего: {result.total} | Успешно: {result.success} | Ошибок: {result.failed}"
        )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.usage)
            return

        raise exc


class BroadcastUserArgs(CommandArgs):
    target: str
    text: Rest


class BroadcastUserHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("broadcast_user", BroadcastUserArgs)
    query = cmd
    usage = "Использование: /broadcast_user <id или @username> <текст>"

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        message = self.ctx.message

        try:
            ok = await self.ctx.broadcast_service.send_to_target(args.target, args.text)
        except ValueError as e:
            await message.answer(f"❌ {e}")
            return

        if ok:
            await message.answer("✅ Сообщение отправлено.")
        else:
            await message.answer(
                "❌ Не удалось отправить — пользователь заблокировал бота."
            )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(self.usage)
            return

        raise exc


class BroadcastRouter(BaseRouter[AppContext]):
    handlers = (
        BroadcastPrivateHandler,
        BroadcastChatsHandler,
        BroadcastAllHandler,
        BroadcastUserHandler,
    )
