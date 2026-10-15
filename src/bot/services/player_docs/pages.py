import difflib
import re
from dataclasses import dataclass
from pathlib import Path

import snowballstemmer
import yaml

from src.bot.exceptions import DocsError

FRONT = "---"
# Оглавление — не раздел: шаблон поста со ссылками на разделы вместо {sections}.
CONTENTS_FILE = "_contents.md"


@dataclass(frozen=True)
class DocPage:
    slug: str
    title: str
    help_words: tuple[str, ...]
    markdown: str


def load_pages(folder: Path) -> list[DocPage]:
    return [
        _page(path)
        for path in sorted(folder.glob("*.md"))
        if not path.name.startswith("_")
    ]


def load_contents_template(folder: Path) -> str:
    path = folder / CONTENTS_FILE
    if not path.exists():
        raise DocsError(f"{path}: нет шаблона оглавления")
    template = path.read_text("utf-8").strip()
    if "{sections}" not in template:
        raise DocsError(f"{path}: в шаблоне нет {{sections}}")
    return template


def _page(path: Path) -> DocPage:
    text = path.read_text("utf-8")
    head, body = _split(text, path)
    meta = yaml.safe_load(head) if head else None
    if not isinstance(meta, dict) or not isinstance(meta.get("title"), str):
        raise DocsError(f"{path.name}: в шапке нужен title")
    words = meta.get("help") or ""
    if not isinstance(words, str):
        raise DocsError(f"{path.name}: help — слова через запятую")
    return DocPage(
        slug=path.stem,
        title=meta["title"],
        help_words=tuple(word.strip().lower() for word in words.split(",") if word.strip()),
        markdown=body.strip(),
    )


def _split(text: str, path: Path) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONT:
        raise DocsError(f"{path.name}: файл начинается с шапки между строками ---")
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == FRONT)
    except StopIteration:
        raise DocsError(f"{path.name}: шапка не закрыта строкой ---") from None
    return "\n".join(lines[1:end]), "\n".join(lines[end + 1 :])


# Подраздел «### …» — одна команда или механика; /help находит его по словам заголовка.
@dataclass(frozen=True)
class DocTopic:
    page: DocPage
    heading: str
    words: tuple[str, ...]
    markdown: str


TOPIC_LEVEL = "### "
SEPARATORS = re.compile(r"[/,()]")
MARKUP = re.compile(r"[*`]")


def topics(page: DocPage) -> list[DocTopic]:
    found: list[DocTopic] = []
    heading: str | None = None
    lines: list[str] = []
    in_code = False

    def close() -> None:
        if heading is not None:
            found.append(DocTopic(page, heading, heading_words(heading), "\n".join(lines).strip()))

    for line in page.markdown.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        is_heading = not in_code and line.startswith("#")
        if is_heading:
            close()
            heading, lines = None, []
            if line.startswith(TOPIC_LEVEL):
                heading = line[len(TOPIC_LEVEL) :].strip()
        if heading is not None:
            lines.append(line)
    close()
    return found


def heading_words(heading: str) -> tuple[str, ...]:
    words = (normalize(part) for part in SEPARATORS.split(MARKUP.sub("", heading)))
    return tuple(word for word in words if word)


def normalize(text: str) -> str:
    return " ".join(text.lower().replace("ё", "е").lstrip("/").split())


def find(pages: list[DocPage], query: str) -> DocTopic | DocPage | None:
    wanted = normalize(query)
    if not wanted:
        return None
    every = [topic for page in pages for topic in topics(page)]
    exact = next((topic for topic in every if wanted in topic.words), None)
    if exact is not None:
        return exact
    page = next(
        (page for page in pages if wanted in (normalize(word) for word in page.help_words)),
        None,
    )
    if page is not None:
        return page
    # «кофе» находит «пить кофе»: все слова запроса есть в одном из слов заголовка.
    tokens = set(wanted.split())
    return next(
        (topic for topic in every if any(tokens <= set(word.split()) for word in topic.words)),
        None,
    )


# Близость, ниже которой слово уже не опечатка, а другое слово.
SUGGEST_CUTOFF = 0.6


def suggest(pages: list[DocPage], query: str, limit: int = 3) -> list[str]:
    words = {word for page in pages for topic in topics(page) for word in topic.words}
    words.update(normalize(word) for page in pages for word in page.help_words)
    # «кофэ» похоже не на «пить кофе» целиком, а на одно его слово — подсказка всё равно фраза.
    phrase_of: dict[str, str] = {word: word for word in sorted(words)}
    for word in sorted(words):
        for token in word.split():
            phrase_of.setdefault(token, word)
    close = difflib.get_close_matches(normalize(query), list(phrase_of), n=limit * 2, cutoff=SUGGEST_CUTOFF)
    return list(dict.fromkeys(phrase_of[key] for key in close))[:limit]


# Основа слова (Snowball): «гулем», «гуля» и «гуль» — одно «гул», вопрос находит раздел.
STEMMER = snowballstemmer.stemmer("russian")
STOP_WORDS = frozenset(
    {"бот", "честор", "как", "что", "это", "где", "мне", "мой", "моя", "ты", "тебя", "тебе",
     "можно", "нужно", "надо", "почему", "зачем", "когда", "сколько", "есть", "или", "так"}
)
WORD = re.compile(r"[а-яa-z0-9]+")
HEADING_WEIGHT = 3


def stems(text: str) -> set[str]:
    words = [word for word in WORD.findall(normalize(text)) if len(word) >= 3 and word not in STOP_WORDS]
    return set(STEMMER.stemWords(words))


def relevant(pages: list[DocPage], question: str, limit: int = 4) -> list[DocTopic]:
    asked = stems(question)
    scored: list[tuple[int, int, DocTopic]] = []
    for order, topic in enumerate(topic for page in pages for topic in topics(page)):
        body = stems(f"{topic.markdown} {' '.join(topic.page.help_words)}")
        score = HEADING_WEIGHT * len(asked & stems(topic.heading)) + len(asked & body)
        if score:
            scored.append((-score, order, topic))
    return [topic for _, _, topic in sorted(scored)[:limit]]


def index(pages: list[DocPage]) -> str:
    return "\n".join(
        f"- {page.title}: {'; '.join(topic.heading for topic in topics(page))}" for page in pages
    )
