import json
from pathlib import Path

import pytest

DIALOGS = json.loads((Path(__file__).parents[1] / "dialogs.json").read_text("utf-8"))


@pytest.mark.parametrize("text", ["бот", "Бот", "БОТ"])
async def test_answers_to_bot_in_any_case(send, text):
    replies = await send(text)

    assert len(replies) == 1
    assert replies[0] in DIALOGS["bot"]


@pytest.mark.parametrize("text", ["привет", "бот привет", "Бот ", "бота"])
async def test_ignores_everything_else(send, text):
    # как F.text.lower() == "бот" в aiogram: строгое равенство, без обрезки пробелов
    assert await send(text) == []


async def test_polls_messages_and_callbacks(send):
    # callback_query нужен кнопкам перевода; chat_member/my_chat_member —
    # chat_member_update_routers (вход/выход участников)
    assert send.dispatcher.used_update_types() == {
        "message",
        "callback_query",
        "chat_member",
        "my_chat_member",
    }


async def test_link_previews_are_disabled_like_in_prod(feed, telegram):
    # DefaultBotProperties(link_preview_is_disabled=True) у прода: Bot.defaults
    from .conftest import message_update

    await feed(message_update("бот"))

    (body,) = telegram.bodies("sendMessage")
    assert body["link_preview_options"] == {"is_disabled": True}
