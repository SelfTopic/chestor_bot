"""Документация для игроков: Markdown-файлы из docs/players/ становятся rich-постами канала.
Повторный запуск правит только изменившиеся посты, удалённый файл — удаляет пост."""

from pathlib import Path

import pytest

from src.bot.services.notify import TelegramDocsChannel
from src.bot.services.player_docs import PlayerDocsService, load_pages
from src.bot.services.player_docs.pages import load_contents_template

CHANNEL = "@docs_test"


def page(folder: Path, name: str, title: str, body: str) -> None:
    (folder / name).write_text(f"---\ntitle: {title}\nhelp: {title.lower()}\n---\n{body}\n")


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    (tmp_path / "_contents.md").write_text("# Оглавление\n\n{sections}\n")
    page(tmp_path, "01-hunger.md", "Голод", "# Голод\n\nтекст про голод")
    page(tmp_path, "02-duels.md", "Дуэли", "# Дуэли\n\nтекст про дуэли")
    return tmp_path


@pytest.fixture
def publish(dispatcher, telegram, session_factory, folder):
    telegram.results["pinChatMessage"] = True
    service = PlayerDocsService(session_factory, folder)

    async def _publish():
        telegram.calls.clear()
        return await service.publish(TelegramDocsChannel(dispatcher.api, CHANNEL), CHANNEL)

    return _publish


async def test_first_run_posts_every_section_and_a_pinned_contents(publish, telegram):
    report = await publish()

    assert report.published == ["01-hunger", "02-duels", "_contents"]
    posts = [body["rich_message"]["markdown"] for body in telegram.bodies("sendRichMessage")]
    assert posts[:2] == ["# Голод\n\nтекст про голод", "# Дуэли\n\nтекст про дуэли"]
    assert "- [Голод](https://t.me/docs_test/100)" in posts[2]
    (pin,) = telegram.bodies("pinChatMessage")
    assert pin["chat_id"] == CHANNEL


async def test_unchanged_docs_touch_nothing_and_an_edit_touches_one_post(
    publish, telegram, folder
):
    await publish()

    await publish()
    assert telegram.calls == []

    page(folder, "02-duels.md", "Дуэли", "# Дуэли\n\nновый текст")
    report = await publish()
    assert report.edited == ["02-duels"]
    (edit,) = telegram.bodies("editMessageText")
    assert edit["rich_message"]["markdown"] == "# Дуэли\n\nновый текст"


async def test_removed_section_loses_its_post_and_its_contents_line(publish, telegram, folder):
    await publish()

    (folder / "01-hunger.md").unlink()
    report = await publish()

    assert report.deleted == ["01-hunger"]
    assert len(telegram.bodies("deleteMessage")) == 1
    (contents,) = telegram.bodies("editMessageText")
    assert "Голод" not in contents["rich_message"]["markdown"]


def test_real_docs_have_valid_headers_and_contents_template() -> None:
    folder = Path("docs/players")

    pages = load_pages(folder)

    assert pages and all(page.title and page.markdown for page in pages)
    assert "{sections}" in load_contents_template(folder)
