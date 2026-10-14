"""«бот найди …»: поиск Tavily и краткий ответ модели по найденным фрагментам.

Вместо Tavily и Cloud.ru — один фейковый сервер: /search отдаёт заданные фрагменты,
/v1/chat/completions — заданный ответ. Запрос к ним идёт в after_handle.
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from aiohttp import web

from src.bot.dialogs import Dialogs
from src.bot.services.llm import LlmClient
from src.bot.services.search import SearchService, TavilyClient

from .conftest import message_update, only_text, owner_dict, phrase_texts

SEARCH = Dialogs.fun.search
MODEL = "searcher"
GROUP = -100


class FakeSearch:
    def __init__(self) -> None:
        self.reply = "Кагуне — охотничий орган гуля."
        self.fail_search = False
        self.queries: list[dict[str, Any]] = []
        self.asked: list[dict[str, Any]] = []

    async def search(self, request: web.Request) -> web.Response:
        self.queries.append(await request.json())
        if self.fail_search:
            return web.json_response({"detail": "boom"}, status=500)
        results = [{"title": "Кагуне", "content": "Кагуне — орган из RC-клеток.", "url": "u"}]
        return web.json_response({"results": results})

    async def complete(self, request: web.Request) -> web.Response:
        self.asked.append(await request.json())
        return web.json_response({"choices": [{"message": {"content": self.reply}}]})


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
async def search(dispatcher, telegram, clock) -> AsyncIterator[FakeSearch]:
    telegram.results["getChatAdministrators"] = [owner_dict(99)]
    fake = FakeSearch()
    app = web.Application()
    app.router.add_post("/search", fake.search)
    app.router.add_post("/v1/chat/completions", fake.complete)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]

    llm = LlmClient(f"http://127.0.0.1:{port}/v1", "key", retry_delay=0)
    dispatcher.search_service = SearchService(
        llm,
        TavilyClient("key", url=f"http://127.0.0.1:{port}/search"),
        enabled=True,
        model=MODEL,
        daily_limit=2,
        cooldown=60,
        timeout=5,
        clock=clock,
    )
    yield fake
    await dispatcher.search_service.close()
    await llm.close()
    await runner.cleanup()


def ask(text: str, uid: int = 7) -> dict[str, Any]:
    return message_update(text, uid=uid, chat=GROUP)


async def test_answer_is_written_from_found_fragments(feed, settle, telegram, search):
    await feed(ask("бот найди что такое кагуне"))
    await settle()

    assert [b["action"] for b in telegram.bodies("sendChatAction")] == ["typing"]
    (sent,) = telegram.bodies("sendMessage")
    assert sent["text"] == search.reply
    assert sent["reply_parameters"]
    (query,) = search.queries
    assert query["query"] == "что такое кагуне"
    (asked,) = search.asked
    assert asked["model"] == MODEL
    assert "Кагуне — орган из RC-клеток." in asked["messages"][1]["content"]


async def test_empty_query_gets_usage(send, search):
    (reply,) = await send("честор найди", chat=GROUP)

    assert reply == only_text(SEARCH.usage())
    assert search.queries == []


async def test_same_player_waits_for_cooldown(feed, settle, telegram, search, clock):
    await feed(ask("бот найди что такое кагуне"))
    await settle()

    clock.now += 45
    await feed(ask("бот найди кто такой Канеки"))
    await settle()

    assert telegram.sent[0] in phrase_texts(SEARCH.cooldown(seconds=15))
    assert len(search.queries) == 1

    clock.now += 15
    await feed(ask("бот найди кто такой Канеки"))
    await settle()
    assert len(search.queries) == 2


async def test_daily_limit_is_shared_by_the_chat(feed, settle, telegram, search):
    for uid in (7, 8):
        await feed(ask("бот найди что такое кагуне", uid=uid))
    await settle()

    await feed(ask("бот найди что такое кагуне", uid=9))
    await settle()

    assert telegram.sent[0] in phrase_texts(SEARCH.limit_reached())
    assert len(search.queries) == 2


async def test_failed_search_is_reported_without_asking_the_model(
    feed, settle, telegram, search
):
    search.fail_search = True

    await feed(ask("бот найди что такое кагуне"))
    await settle()

    assert telegram.sent[0] in phrase_texts(SEARCH.failed())
    assert search.asked == []


async def test_without_keys_search_is_off(send, dispatcher, search):
    dispatcher.search_service = SearchService(
        LlmClient("http://unused", ""),
        TavilyClient(""),
        enabled=False,
        model=MODEL,
        daily_limit=2,
        cooldown=60,
        timeout=5,
    )

    (reply,) = await send("бот найди что такое кагуне", chat=GROUP)

    assert reply == only_text(SEARCH.unavailable())
    assert search.queries == []
