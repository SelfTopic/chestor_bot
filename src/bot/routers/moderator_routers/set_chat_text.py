"""
Общий каркас «новые правила / новое приветствие / новое прощание <текст>».

Исправленные прод-баги: прод ловил команду по началу текста и срезал префикс по
длине, поэтому срабатывал и на «новые правилаX», а в сохранённом тексте оставался
пробел в начале (" Не спамить"). Здесь это Command целыми словами, а текст — Rest:
края обрезаются, переводы строк внутри сохраняются. Пустой текст, как у прода,
проверяет ChatService (для правил это ChatRulesError, ответ — global_error).
"""

from typing import Any

from selfrot import CommandArgs, Rest
from selfrot.filter import Command

from src.bot.exceptions import ChatNotFoundInDatabase

from ...context import AppContext


class ChatTextArgs(CommandArgs):
    value: Rest = ""  # пустой отвергает не разбор, а ChatService, как у прода


def chat_text_command(name: str) -> Command[ChatTextArgs]:
    return Command(name, ChatTextArgs, prefixes="", ignore_case=True)


class SetChatTextHandler:
    """Сохранить текст через ChatService и ответить новым значением. Наследник:
    второе основание MessageHandler[AppContext[TextMessage]] (как и в targeting.py,
    заголовок библиотека проверяет только на прямых базах), cmd, query = cmd, apply."""

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
