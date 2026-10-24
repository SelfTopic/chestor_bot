import asyncio
import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

USER_AGENT = "chestor_bot/1.0 (https://github.com/SelfTopic/chestor_bot; quote feature)"

ROW_RE = re.compile(
    r'<div class="views-row views-row-\d+ quotes-row">.*?'
    r'(?=<div class="views-row views-row-\d+ quotes-row">|\Z)',
    re.S,
)
BODY_RE = re.compile(r'<div class="field-name-body">\s*<p>(.*?)</p>', re.S)
# У ссылки на персонажа есть title="Цитируемый персонаж" между href и закрывающей «>».
CHARACTER_RE = re.compile(r'<a href="https://citaty\.info/character/([^"]+)"[^>]*>(.*?)</a>')
QUOTE_ID_RE = re.compile(r"citaty\.info/quote/(\d+)")
SEASON_RE = re.compile(r"field-name-field-season.*?\?season=(\d+)", re.S)
SERIES_RE = re.compile(r"field-name-field-series.*?season=\d+&amp;series=(\d+)", re.S)
TAG_RE = re.compile(r"<[^>]+>")
ENTITIES = {
    "&laquo;": "«",
    "&raquo;": "»",
    "&ndash;": "–",
    "&mdash;": "—",
    "&nbsp;": " ",
    "&quot;": '"',
    "&amp;": "&",
}


@dataclass(frozen=True)
class Quote:
    id: int
    source: str
    character_slug: str
    character_name: str
    season: int | None
    series: int | None
    text: str


def _clean_text(html: str) -> str:
    text = TAG_RE.sub("", html)
    for entity, char in ENTITIES.items():
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def _parse_page(html: str, source: str) -> list[Quote]:
    quotes = []
    for row_match in ROW_RE.finditer(html):
        block = row_match.group(0)
        body = BODY_RE.search(block)
        character = CHARACTER_RE.search(block)
        quote_id = QUOTE_ID_RE.search(block)
        if not body or not character or not quote_id:
            continue
        season = SEASON_RE.search(block)
        series = SERIES_RE.search(block)
        quotes.append(
            Quote(
                id=int(quote_id.group(1)),
                source=source,
                character_slug=character.group(1),
                character_name=_clean_text(character.group(2)),
                season=int(season.group(1)) if season else None,
                series=int(series.group(1)) if series else None,
                text=_clean_text(body.group(1)),
            )
        )
    return quotes


class QuoteScraper:
    sources = {
        "anime": "https://citaty.info/anime/tokiiskii-gul-tokyo-ghoul",
        "comics": "https://citaty.info/comics/tokiiskii-gul-tokyo-ghoul",
    }

    def __init__(self, output_path: str | Path, request_delay: float = 0.5):
        self.output_path = Path(output_path)
        self.request_delay = request_delay

    async def _fetch_source(
        self, session: aiohttp.ClientSession, source: str, base_url: str
    ) -> list[Quote]:
        quotes: list[Quote] = []
        seen_ids: set[int] = set()
        page = 0
        # Пейджер на сайте показывает только несколько соседних номеров страниц
        # (между ними «…»), реальных страниц больше — поэтому идём вперёд сами.
        # После последней страницы сайт либо отдаёт пустую страницу (anime), либо
        # зацикливается на содержимом первой страницы (comics) — в обоих случаях
        # останавливаемся, как только страница не принесла ни одной новой цитаты.
        while True:
            url = base_url if page == 0 else f"{base_url}?page={page}"
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
            new_quotes = [q for q in _parse_page(html, source) if q.id not in seen_ids]
            if not new_quotes:
                break
            quotes += new_quotes
            seen_ids.update(q.id for q in new_quotes)
            page += 1
            await asyncio.sleep(self.request_delay)
        return quotes

    async def scrape_all(self) -> list[Quote]:
        quotes: list[Quote] = []
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20),
            headers={"User-Agent": USER_AGENT},
        ) as session:
            for source, base_url in self.sources.items():
                source_quotes = await self._fetch_source(session, source, base_url)
                logger.info(f"{source}: {len(source_quotes)} цитат")
                quotes += source_quotes
        return quotes

    def write(self, quotes: list[Quote]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(quote) for quote in sorted(quotes, key=lambda q: q.id)]
        self.output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    async def run(self) -> list[Quote]:
        quotes = await self.scrape_all()
        self.write(quotes)
        return quotes


__all__ = ["Quote", "QuoteScraper"]
