"""Язык ответа: в группе — язык чата, в личке — выбранный игроком, иначе язык его Telegram."""

import pytest
from sqlalchemy import update

from src.bot.dialogs import DIALOGS_DIR, Dialogs
from src.bot.services.dialog import DialogService
from src.database.models import Chat, User

from .conftest import matches_phrase, message_update, owner_dict, phrase_texts

GROUP = -100123


@pytest.fixture
def english(dispatcher, tmp_path):
    for path in DIALOGS_DIR.glob("*.yaml"):
        (tmp_path / path.name).write_text(path.read_text("utf-8"), "utf-8")
    (tmp_path / "en").mkdir()
    (tmp_path / "en" / "common.yaml").write_text("start: 'Hi {name}'\n", "utf-8")
    dispatcher.dialog_service = DialogService(tmp_path)


async def start(feed, telegram_language: str | None, chat: int | None = None) -> str:
    update = message_update("/start", uid=42, chat=chat)
    sender = update["message"]["from"]
    if telegram_language is None:
        del sender["language_code"]
    else:
        sender["language_code"] = telegram_language
    (reply,) = (await feed(update)).sent
    return reply


@pytest.mark.parametrize("telegram_language", ["en", "en-GB", "fa", None])
async def test_new_player_gets_english_unless_telegram_is_russian(
    feed, english, telegram_language
):
    assert await start(feed, telegram_language) == "Hi Вася"


async def test_russian_telegram_gets_russian(feed, english):
    assert await start(feed, "ru") in phrase_texts(Dialogs.start(name="Вася"))


async def test_chosen_language_beats_telegram_language(feed, english, session_factory):
    await start(feed, "en")
    async with session_factory() as session:
        await session.execute(update(User).values(language="ru"))
        await session.commit()

    assert await start(feed, "en") in phrase_texts(Dialogs.start(name="Вася"))


async def test_group_speaks_chat_language_not_sender_language(
    feed, english, session_factory, telegram
):
    telegram.results["getChatAdministrators"] = [owner_dict(99)]
    assert await start(feed, "en", chat=GROUP) in phrase_texts(
        Dialogs.start(name="Вася")
    )

    async with session_factory() as session:
        await session.execute(update(Chat).values(language="en"))
        await session.commit()

    assert await start(feed, "ru", chat=GROUP) == "Hi Вася"


@pytest.mark.parametrize(
    ("text", "phrase"),
    [
        ("profile", "profile.card"),
        ("race profile", "profile.card"),
        ("bal", "balance"),
        ("send", "transfer.usage"),
        ("bet", "lottery.usage"),
        # цвет понят, раз дошло до проверки ставки
        ("bet red 1", "lottery.bet_out_of_range"),
        ("grow kagune", "ghoul.new"),
        ("snap", "ghoul.not_a_ghoul"),
        ("drink coffee", "ghoul.not_a_ghoul"),
        ("eat human", "ghoul.not_a_ghoul"),
        ("hunger", "ghoul.not_a_ghoul"),
        ("regen", "ghoul.not_a_ghoul"),
        ("train", "ghoul.not_a_ghoul"),
        ("cp", "ghoul.not_a_ghoul"),
        ("combat power", "ghoul.not_a_ghoul"),
        ("evolution", "ghoul.not_a_ghoul"),
        ("mutation", "ghoul.not_a_ghoul"),
        ("quiz", "ghoul.not_a_ghoul"),
        ("promo x", "ghoul.not_a_ghoul"),
        ("top snap", "ghoul.not_a_ghoul"),
        ("top cp", "ghoul.not_a_ghoul"),
        ("top kagune", "ghoul.not_a_ghoul"),
    ],
)
async def test_english_command_words(send, text, phrase):
    (reply,) = await send(text, uid=42)

    assert matches_phrase(reply, phrase)

