import json
import random
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

QUOTES_PATH = Path("src/assets/data/quotes/quotes.json")
MATCH_CUTOFF = 0.8

# Сайт отдаёт одного и того же персонажа под разными слагами/написаниями имени —
# эти группы сводят их в одного человека для поиска. Арата/Аято/Тоука Киришима сюда
# не входят: это три разных персонажа с общей фамилией, не варианты одного имени.
CHARACTER_ALIASES: tuple[tuple[str, ...], ...] = (
    ("Канеки", "Канеки Кен / Хайсе Сасаки"),
    ("Ризе Камиширо", "Ризэ Камиширо"),
    ("Цукияма Шу", "Цукияма Шу (Гурман)", "Шу Цукияма"),
    ("Джузо Сузуя", "Дзюдзо Судзуя", "Сузуя Джузо"),
    ("Сейдо Такидзава", "Сейдо Такизава"),
    ("Куки Урие", "Урие Куки"),
    ("Аято Киришима", "Аято Кирисима"),
    ("Ренджи Йомо", "Рэндзи"),
    ("Ута", "Ута (Uta)"),
)

WORD_RE = re.compile(r"[а-яёa-z]+", re.IGNORECASE)


def _words(text: str) -> frozenset[str]:
    return frozenset(w.lower() for w in WORD_RE.findall(text))


@dataclass(frozen=True)
class Quote:
    character_name: str
    text: str
    source: str
    season: int | None
    series: int | None


class QuoteService:
    # Файл не в гите (как остальные данные в src/assets) и появляется только после
    # fetch_quotes.py — без него сервис просто не находит цитат, а не роняет бота.
    def __init__(self, path: Path = QUOTES_PATH) -> None:
        raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        self._quotes = [
            Quote(
                character_name=q["character_name"],
                text=q["text"],
                source=q["source"],
                season=q["season"],
                series=q["series"],
            )
            for q in raw
        ]

        alias_group: dict[str, frozenset[str]] = {}
        for aliases in CHARACTER_ALIASES:
            group = frozenset(aliases)
            for name in aliases:
                alias_group[name] = group

        # Группы считаются от реально встретившихся на сайте имён, а не от хардкода:
        # новый персонаж после пересборки quotes.json сам попадёт сюда одиночной группой.
        self._groups: list[tuple[frozenset[str], frozenset[str]]] = []
        seen: set[str] = set()
        for quote in self._quotes:
            if quote.character_name in seen:
                continue
            group = alias_group.get(quote.character_name, frozenset({quote.character_name}))
            seen |= group
            self._groups.append((group, _words(" ".join(group))))

    @staticmethod
    def _words_match(query_words: frozenset[str], alias_words: frozenset[str]) -> bool:
        return all(
            any(SequenceMatcher(None, query_word, alias_word).ratio() >= MATCH_CUTOFF
                for alias_word in alias_words)
            for query_word in query_words
        )

    def random_quote(self, query: str = "") -> Quote | None:
        if not self._quotes:
            return None

        words = _words(query)
        if not words:
            return random.choice(self._quotes)

        raw_names: set[str] = set()
        for group, alias_words in self._groups:
            if self._words_match(words, alias_words):
                raw_names |= group

        pool = [quote for quote in self._quotes if quote.character_name in raw_names]
        return random.choice(pool) if pool else None


__all__ = ["Quote", "QuoteService"]
