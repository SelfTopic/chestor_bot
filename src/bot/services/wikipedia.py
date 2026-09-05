import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)

WIKIPEDIA_SUMMARY_URL = "https://ru.wikipedia.org/api/rest_v1/page/summary/{title}"
USER_AGENT = "chestor_bot/1.0 (https://github.com/SelfTopic/chestor_bot; wordle feature)"


@dataclass
class WikipediaSummary:
    extract: str
    url: str


class WikipediaService:
    """Короткое описание слова из русской Википедии для карточки завершения игры."""

    async def get_summary(self, word: str) -> Optional[WikipediaSummary]:
        title = word.strip().capitalize()

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5),
                headers={"User-Agent": USER_AGENT},
            ) as session:
                async with session.get(
                    WIKIPEDIA_SUMMARY_URL.format(title=quote(title))
                ) as response:
                    if response.status != 200:
                        return None
                    data = await response.json()

        except (aiohttp.ClientError, TimeoutError):
            logger.warning(
                f"Failed to fetch Wikipedia summary for '{word}'", exc_info=True
            )
            return None

        extract = data.get("extract")
        url = data.get("content_urls", {}).get("desktop", {}).get("page")

        if not extract or not url:
            return None

        return WikipediaSummary(extract=extract, url=url)


__all__ = ["WikipediaService", "WikipediaSummary"]
