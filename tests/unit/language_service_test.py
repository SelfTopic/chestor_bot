"""Язык чата для сообщений вне апдейта: группа — язык чата, личка — язык игрока."""

import pytest
from sqlalchemy import update

from src.bot.repositories import ChatRepository, UserRepository
from src.bot.services.dialog import DialogService
from src.bot.services.language import LanguageService
from src.bot.types.insert import ChatInsert
from src.database.models import Chat

GROUP = -100500


@pytest.fixture
def languages(session):
    return LanguageService(UserRepository(session), ChatRepository(session), DialogService())


@pytest.mark.parametrize(
    ("chosen", "telegram", "expected"),
    [
        ("ru", "en", "ru"),
        (None, "en-GB", "en"),
        (None, "fa", "en"),
        (None, None, "en"),
        (None, "ru", "ru"),
    ],
)
async def test_private_chat_speaks_player_language(
    languages, user_repo, chosen, telegram, expected
):
    await user_repo.upsert(telegram_id=700001, first_name="Ali", telegram_language=telegram)
    if chosen is not None:
        await user_repo.change_data(700001, language=chosen)

    assert await languages.of_chat(700001) == expected


async def test_telegram_language_is_kept_when_an_update_omits_it(languages, user_repo):
    await user_repo.upsert(telegram_id=700001, first_name="Ali", telegram_language="ru")
    await user_repo.upsert(telegram_id=700001, first_name="Ali")

    assert await languages.of_chat(700001) == "ru"


async def test_group_speaks_chat_language(languages, session):
    assert await languages.of_chat(GROUP) == "ru"

    await ChatRepository(session).upsert(
        ChatInsert(telegram_id=GROUP, title="g", username=None, creator_id=1)
    )
    await session.execute(update(Chat).values(language="en"))
    assert await languages.of_chat(GROUP) == "en"
