from typing import Any, ClassVar

from src.bot.exceptions import ChatNotFoundInDatabase

from ...context import AppContext


class SetChatTextHandler:
    """Общий каркас «новые правила/приветствие/прощание <текст>»: снять префикс
    команды с message.text, сохранить остаток через ChatService, ответить новым
    значением. Как и targeting.py, не параметризует MessageHandler[...] сам —
    конкретный заголовок остаётся explicit у каждого хендлера, иначе библиотека не
    сможет проверить его при определении класса (смотрит только на прямые базы)."""

    PREFIX: ClassVar[str]
    ctx: AppContext[Any]

    async def apply(self, telegram_id: int, value: str) -> str:
        raise NotImplementedError

    async def handle(self) -> None:
        message = self.ctx.message
        chat = await self.ctx.chat_service.get_by_telegram_id(message.chat.id)
        if chat is None:
            raise ChatNotFoundInDatabase()

        value = message.text[len(self.PREFIX) :]
        await message.answer(await self.apply(message.chat.id, value))
