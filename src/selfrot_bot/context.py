from dataclasses import dataclass

from selfrot import BaseContext, TEvent

from src.bot.services.dialog import DialogService


@dataclass
class AppContext(BaseContext[TEvent]):
    """Контекст одного апдейта. Сервисы приложения, вместо Provide[Container...]."""

    dialog_service: DialogService
