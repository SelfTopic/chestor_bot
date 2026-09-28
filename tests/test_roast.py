"""Огрызания бота через нейросеть: когда бот зовёт модель, что отправляет и что пишет в журнал.

Вместо Cloud.ru — фейковый сервер с OpenAI-совместимым /chat/completions: классификатор
отвечает заданным вердиктом, генератор — заданной репликой.
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from aiohttp import web
from sqlalchemy import select

from src.bot.dialogs import Dialogs
from src.bot.services.roast import LlmClient, RoastPrompts, RoastService
from src.bot.services.roast import service as roast_module
from src.config import settings
from src.database.models import RoastLog

from .conftest import message_update, only_text, owner_dict, phrase_texts

GROUP = -100
BOT_ID = 1  # getMe у FakeTelegram
ADMIN = 999
CLASSIFIER = "classifier"
GENERATOR = "generator"


class FakeLlm:
    def __init__(self) -> None:
        self.verdict = "да"
        self.reply = "Ага, поплачь. Только клаву не залей."
        self.fail_generation = False
        self.requests: list[dict[str, Any]] = []

    def asked(self, model: str) -> list[str]:
        return [r["messages"][1]["content"] for r in self.requests if r["model"] == model]

    async def handle(self, request: web.Request) -> web.Response:
        body = await request.json()
        self.requests.append(body)
        if body["model"] == GENERATOR and self.fail_generation:
            return web.json_response({"error": "boom"}, status=500)
        content = self.verdict if body["model"] == CLASSIFIER else self.reply
        return web.json_response({"choices": [{"message": {"content": content}}]})


@pytest.fixture
async def llm(dispatcher, session_factory, telegram) -> AsyncIterator[FakeLlm]:
    fake = FakeLlm()
    app = web.Application()
    app.router.add_post("/v1/chat/completions", fake.handle)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]

    client = LlmClient(f"http://127.0.0.1:{port}/v1", "key")
    dispatcher.roast_service = RoastService(
        session_factory,
        client,
        RoastPrompts(),
        enabled=True,
        model=GENERATOR,
        classifier_model=CLASSIFIER,
        daily_limit=100,
        timeout=5,
    )
    dispatcher.roast_service.bot_id = BOT_ID
    telegram.results["getChatAdministrators"] = [owner_dict(99)]
    yield fake
    await client.close()
    await runner.cleanup()


def insult(text: str, **extra: Any) -> dict[str, Any]:
    return message_update(text, chat=GROUP, reply_to_uid=BOT_ID, reply_to_name="B", **extra)


async def logged(session_factory) -> list[RoastLog]:
    async with session_factory() as session:
        return list(await session.scalars(select(RoastLog).order_by(RoastLog.id)))


async def test_reply_to_bot_gets_generated_answer_and_is_logged(
    feed, settle, telegram, llm, session_factory
):
    await feed(insult("сам ты бомжиха"))
    await settle()

    (sent,) = telegram.bodies("sendMessage")
    assert sent["text"] == "ага поплачь только клаву не залей"
    assert sent["reply_parameters"]
    (row,) = await logged(session_factory)
    assert (row.message, row.reply, row.bot_message_id) == ("сам ты бомжиха", sent["text"], 100)
    assert "[в ответ боту]: сам ты бомжиха" in llm.asked(CLASSIFIER)[0]


async def test_message_to_someone_else_is_silent_and_not_logged(
    feed, settle, telegram, llm, session_factory
):
    llm.verdict = "нет"

    await feed(insult("пиздец ты задрот"))
    await settle()

    assert telegram.bodies("sendMessage") == []
    assert await logged(session_factory) == []


async def test_plain_chat_does_not_reach_the_model(feed, settle, llm):
    await feed(message_update("го в доту", chat=GROUP))
    await feed(message_update("сам ты бомжиха", reply_to_uid=BOT_ID))  # личка
    await settle()

    assert llm.requests == []


@pytest.mark.parametrize("broken", ["filtered", "failed"])
async def test_unusable_reply_is_silent_but_logged(
    feed, settle, telegram, llm, session_factory, broken
):
    llm.reply = "убейся"
    llm.fail_generation = broken == "failed"

    await feed(insult("бот ты тупой"))
    await settle()

    assert telegram.bodies("sendMessage") == []
    (row,) = await logged(session_factory)
    assert row.filtered == (broken == "filtered")


async def test_long_argument_ends_with_bored_phrase_and_silence(
    feed, settle, telegram, llm, monkeypatch
):
    monkeypatch.setattr(roast_module, "MAX_TURNS", 2)
    answers = []
    # Первое — реплаем боту, дальше спор продолжается без реплаев.
    for update in (insult("бот ты тупой"), *(
        message_update(text, chat=GROUP) for text in ("ты тупой", "и вообще железка", "эй")
    )):
        await feed(update)
        await settle()
        answers.append(telegram.sent)

    assert answers[2] and answers[2][0] in phrase_texts(Dialogs.roast.bored())
    assert answers[3] == []
    assert len(llm.asked(GENERATOR)) == 2

    monkeypatch.setattr(settings, "ADMIN_IDS", [ADMIN])
    await feed(message_update("/roast_reset", uid=ADMIN, chat=GROUP))
    assert telegram.sent == [only_text(Dialogs.admin.roast.reset(count=1))]
    await feed(insult("бот ты тупой"))
    await settle()
    assert telegram.sent == ["ага поплачь только клаву не залей"]


async def test_admin_rates_a_roast(feed, settle, telegram, llm, session_factory, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_IDS", [ADMIN])
    await feed(insult("сам ты бомжиха"))
    await settle()

    await feed(message_update("/good", uid=ADMIN, chat=GROUP, reply_to_uid=BOT_ID,
                              reply_extra={"message_id": 100, "text": "ага"}))
    (answer,) = telegram.sent
    await feed(message_update("/bad", uid=ADMIN, chat=GROUP, reply_to_uid=BOT_ID))
    (unknown,) = telegram.sent

    (row,) = await logged(session_factory)
    assert row.rating == 1
    assert answer == only_text(Dialogs.admin.roast.good())
    assert unknown == only_text(Dialogs.admin.roast.not_found())


async def test_model_sees_whom_the_bot_answered(feed, settle, llm):
    await feed(message_update("бот", uid=8, first_name="Петя", chat=GROUP))
    await feed(insult("пиздец ты задрот", reply_extra={"message_id": 100, "text": "чо надо"}))
    await settle()

    assert "бот → Петя: чо надо" in llm.asked(CLASSIFIER)[0]


async def test_reply_to_someone_elses_quarrel_is_marked(feed, settle, llm):
    await feed(message_update("бот ты тупой", uid=8, first_name="Петя", chat=GROUP))
    await settle()
    comeback = {"message_id": 100, "text": llm.reply}
    await feed(insult("хуйло алё", reply_extra=comeback))
    await settle()

    assert f"бот → Петя (перепалка): {llm.reply}" in llm.asked(CLASSIFIER)[1]
