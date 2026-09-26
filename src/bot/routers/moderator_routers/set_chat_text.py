from typing import Any

from selfrot import CommandArgs, Rest
from selfrot.filter import Command

from src.bot.exceptions import ChatNotFoundInDatabase

from ...context import AppContext


class ChatTextArgs(CommandArgs):
    value: Rest = ""


def chat_text_command(name: str) -> Command[ChatTextArgs]:
    return Command(name, ChatTextArgs, prefixes="", ignore_case=True)


class SetChatTextHandler:
    cmd: Command[ChatTextArgs]
    ctx: AppContext[Any]

    async def apply(self, telegram_id: int, value: str) -> str:
        raise NotImplementedError

    async def handle(self) -> None:
        message = self.ctx.message
        chat = await self.ctx.chat_service.get_by_telegram_id(message.chat.id)
        if chat is None:
            raise ChatNotFoundInDatabase()

        value = self.cmd.parse(self.ctx).value
        await message.answer(await self.apply(message.chat.id, value))
