from selfrot import Bot, BotDefaults
from selfrot.types import LinkPreviewOptions

from src.config import settings


def _proxy() -> str | None:
    # То же условие, что у прода в src/bot/__main__.py (в том числе HTTP_PROXY только
    # при заданном HTTPS_PROXY); пустая строка значит «без прокси».
    proxy = (
        settings.HTTP_PROXY
        if settings.HTTPS_PROXY
        else settings.ALL_PROXY
        if settings.ALL_PROXY
        else None
    )
    return proxy or None


class AppBot(Bot):
    """Настройки бота: диспетчер создаёт его сам (bot = AppBot), поэтому атрибутами."""

    # DefaultBotProperties(link_preview_is_disabled=True) у прода
    defaults = BotDefaults(link_preview_options=LinkPreviewOptions(is_disabled=True))
    proxy = _proxy()
