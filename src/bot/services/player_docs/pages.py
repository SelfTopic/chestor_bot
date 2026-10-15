from dataclasses import dataclass
from pathlib import Path

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
