from src.bot.dialogs import BASE_LANGUAGE, LineText
from src.bot.repositories import ChatRepository, UserRepository
from src.bot.services.dialog import DialogService


class LanguageService:
    def __init__(
        self,
        user_repository: UserRepository,
        chat_repository: ChatRepository,
        dialog_service: DialogService,
    ) -> None:
        self.user_repository = user_repository
        self.chat_repository = chat_repository
        self.dialog_service = dialog_service

    async def text_for(self, chat_id: int) -> LineText:
        return self.dialog_service.text_in(await self.of_chat(chat_id))

    async def of_chat(self, chat_id: int) -> str:
        # У лички id чата совпадает с id игрока.
        if chat_id > 0:
            return await self.of_user(chat_id)
        # Чат, чьё добавление бот не застал, говорит по-русски, как все чаты до переводов.
        return await self.chat_repository.language(chat_id) or BASE_LANGUAGE

    async def of_user(self, telegram_id: int) -> str:
        languages = await self.user_repository.languages(telegram_id)
        chosen, telegram = languages if languages is not None else (None, None)
        return chosen or self.dialog_service.language_for(telegram)


__all__ = ["LanguageService"]
