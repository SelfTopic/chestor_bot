from typing import Any

from selfrot import CommandArgs, Rest
from selfrot.filter import AnyCommand, Command

from src.bot.exceptions import ChatNotFoundInDatabase

from ...context import AppContext


class ChatTextArgs(CommandArgs):
    # Пустой текст должен отвергнуть ChatService своей ошибкой, а не разбор аргументов.
    value: Rest = ""


def chat_text_command(*names: str) -> AnyCommand[ChatTextArgs]:
    return AnyCommand(
        *(Command(name, ChatTextArgs, prefixes="", ignore_case=True) for name in names)
    )


class SetChatTextHandler:
    cmd: AnyCommand[ChatTextArgs]
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
