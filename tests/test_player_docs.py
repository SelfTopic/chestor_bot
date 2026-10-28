"""Документация для игроков: Markdown-файлы из docs/players/ становятся rich-постами канала,
а /help показывает раздел или подраздел про нужную команду. Повторный запуск правит только
изменившиеся посты; у каждой команды игроков есть свой подраздел."""

import re
from pathlib import Path

import pytest

from src.bot.dialogs import Dialogs
from src.bot.repositories import DocsPostRepository, PublishedPost
from src.bot.services.notify import TelegramDocsChannel
from src.bot.services.player_docs import PlayerDocsService, load_pages
from src.bot.services.player_docs.pages import load_contents_template, normalize, topics
from src.config import settings

from .conftest import button_data, callback_update, only_text

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


async def test_edit_telegram_finds_unchanged_is_not_an_error(publish, telegram, folder):
    await publish()
    page(folder, "02-duels.md", "Дуэли", "# Дуэли\n\nновый текст")
    telegram.errors["editMessageText"] = (
        400,
        "Bad Request: message is not modified: specified new message content and reply "
        "markup are exactly the same as a current content and reply markup of the message",
    )

    report = await publish()

    assert report.edited == ["02-duels"]


async def test_removed_section_loses_its_post_and_its_contents_line(publish, telegram, folder):
    await publish()

    (folder / "01-hunger.md").unlink()
    report = await publish()

    assert report.deleted == ["01-hunger"]
    assert len(telegram.bodies("deleteMessage")) == 1
    (contents,) = telegram.bodies("editMessageText")
    assert "Голод" not in contents["rich_message"]["markdown"]


@pytest.mark.parametrize("folder", [Path("docs/players"), Path("docs/players/en")])
def test_real_docs_have_valid_headers_and_contents_template(folder: Path) -> None:
    pages = load_pages(folder)

    assert pages and all(page.title and page.markdown for page in pages)
    assert "{sections}" in load_contents_template(folder)


ROUTERS = Path("src/bot/routers")
# Команды владельца бота и обмен с юзерботом игрокам не нужны и в справку не идут.
NOT_FOR_PLAYERS = (ROUTERS / "creator", ROUTERS / "system")
TRIGGERS = (
    re.compile(r'\bCommand\(\s*"([^"]+)"'),
    re.compile(r'\bText\(\s*"([^"]+)"'),
    re.compile(r'\bchat_text_command\(\s*"([^"]+)"'),
    re.compile(r'\btop_command\(\s*"([^"]+)"'),
)
BOT_TRIGGERS = (re.compile(r'\bbot_command\(\s*"([^"]+)"'), re.compile(r'f"\{name\} ([^"{]+)"'))
SLASH_AND_TEXT = re.compile(r'\bcommand\(\s*"([a-z_]+)",\s*(\([^)]*\)|"[^"]*"|[A-Z_]+)')
WORD_TUPLES = re.compile(r"^([A-Z_]+_WORDS) = \(([^)]*)\)", re.MULTILINE)


def player_triggers() -> set[str]:
    sources = [
        path
        for path in ROUTERS.rglob("*.py")
        if not any(path.is_relative_to(skip) for skip in NOT_FOR_PLAYERS)
    ]
    found: set[str] = set()
    for path in sources:
        text = path.read_text("utf-8")
        tuples = {name: re.findall(r'"([^"]+)"', words) for name, words in WORD_TUPLES.findall(text)}
        for pattern in TRIGGERS:
            found.update(pattern.findall(text))
        for pattern in BOT_TRIGGERS:
            found.update(f"бот {action}" for action in pattern.findall(text))
        for slash, words in SLASH_AND_TEXT.findall(text):
            found.add(slash)
            found.update(tuples.get(words) or re.findall(r'"([^"]+)"', words))
    return found


CYRILLIC = re.compile(r"[а-яё]", re.IGNORECASE)


# Русские слова команд ищутся в русской справке, всё латиницей (английские слова и слэш-команды)
# — в английской.
@pytest.mark.parametrize(
    ("folder", "is_russian"), [(Path("docs/players"), True), (Path("docs/players/en"), False)]
)
def test_every_player_command_has_its_own_help_topic(folder: Path, is_russian: bool) -> None:
    words = {word for page in load_pages(folder) for topic in topics(page) for word in topic.words}

    missing = sorted(
        trigger
        for trigger in player_triggers()
        if bool(CYRILLIC.search(trigger)) == is_russian and normalize(trigger) not in words
    )

    assert missing == [], f"нет подраздела «### …» в {folder} для: {missing}"


async def test_help_lists_sections_with_links_to_the_channel(
    send, telegram, session_factory, monkeypatch
):
    monkeypatch.setattr(settings, "DOCS_CHANNEL", "@chestor_docs")
    async with session_factory() as session:
        await DocsPostRepository(session).save("@chestor_docs", "04-hunger", PublishedPost(7, "x"))
        await session.commit()

    await send("/help")

    (body,) = telegram.bodies("sendRichMessage")
    markdown = body["rich_message"]["markdown"]
    assert "- [Голод и жертвы](https://t.me/chestor_docs/7)" in markdown
    assert "- Деньги" in markdown


async def test_help_word_shows_its_topic_with_a_link_to_the_whole_section(
    send, telegram, session_factory, monkeypatch
):
    monkeypatch.setattr(settings, "DOCS_CHANNEL", "@chestor_docs")
    async with session_factory() as session:
        await DocsPostRepository(session).save("@chestor_docs", "06-economy", PublishedPost(9, "x"))
        await session.commit()
    coffee = next(
        topic
        for page in load_pages(Path("docs/players"))
        for topic in topics(page)
        if "пить кофе" in topic.words
    )

    await send("/help кофе")

    (body,) = telegram.bodies("sendRichMessage")
    assert body["rich_message"]["markdown"] == coffee.markdown
    (row,) = body["reply_markup"]["inline_keyboard"]
    assert row[0]["url"] == "https://t.me/chestor_docs/9"


async def test_help_for_an_unknown_word(send):
    (reply,) = await send("/help абракадабра")

    assert reply == only_text(Dialogs.help.not_found(query="абракадабра"))


async def test_typo_gets_suggestions_and_a_press_turns_into_the_topic(feed, send, telegram):
    snap = next(
        topic
        for page in load_pages(Path("docs/players"))
        for topic in topics(page)
        if "щелк" in topic.words
    )

    (reply,) = await send("/help щелу")

    assert reply == only_text(Dialogs.help.did_you_mean(query="щелу"))
    (body,) = telegram.bodies("sendMessage")
    await feed(callback_update(button_data(body, "щелк")))
    (edit,) = telegram.bodies("editMessageText")
    assert edit["rich_message"]["markdown"] == snap.markdown
