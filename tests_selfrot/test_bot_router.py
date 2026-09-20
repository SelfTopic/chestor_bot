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


async def test_polls_only_messages(send):
    assert send.dispatcher.used_update_types() == {"message"}
