from selfrot import Bot, BotDefaults
from selfrot.types import LinkPreviewOptions

from src.config import settings


def _proxy() -> str | None:
    proxy = (
        settings.HTTP_PROXY
        if settings.HTTPS_PROXY
        else settings.ALL_PROXY
        if settings.ALL_PROXY
        else None
    )
    return proxy or None


class AppBot(Bot):
    defaults = BotDefaults(link_preview_options=LinkPreviewOptions(is_disabled=True))
    proxy = _proxy()
