"""
Тесты порта на selfrotgram. Лежат отдельно от tests/: тот conftest поднимает Docker
с Postgres для каждого теста, а порту он не нужен. Telegram здесь фейковый
(HTTP-сервер на localhost), настоящий токен и сеть не используются.
"""

import json
import os
from collections.abc import AsyncIterator
from typing import Any

import pytest
from aiohttp import web
from pydantic import TypeAdapter

# src.config требует эти настройки при импорте (а импорт DialogService тянет весь
# src.bot.services). Значения фиктивные и перекрывают .env: тесты от него не зависят.
for name, value in {
    "BOT_TOKEN": "123456:TEST",
    "POSTGRES_DATABASE": "test",
    "POSTGRES_USERNAME": "test",
    "POSTGRES_PASSWORD": "test",
    "POSTGRES_HOSTNAME": "localhost",
    "PGADMIN_DEFAULT_EMAIL": "test@example.org",
    "PGADMIN_DEFAULT_PASSWORD": "test",
    "GHOUL_QUIZ_API_KEY": "test",
}.items():
    os.environ.setdefault(name, value)

from selfrot.client.telegram import TELEGRAM_API  # noqa: E402
from selfrot.types import Update  # noqa: E402


class FakeTelegram:
    """Записывает вызовы Bot API и отвечает заготовками."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    @property
    def sent(self) -> list[str]:
        """Тексты всех sendMessage."""
        return [b["text"] for m, b in self.calls if m == "sendMessage"]

    async def handle(self, request: web.Request) -> web.Response:
        method = request.match_info["method"]
        self.calls.append((method, json.loads(await request.text() or "{}")))

        result: Any = {
            "getMe": {"id": 1, "is_bot": True, "first_name": "B", "username": "dev_bot"}
        }.get(
            method,
            {
                "message_id": 100,
                "date": 5,
                "chat": {"id": 7, "type": "private"},
                "text": "x",
            },
        )
        return web.json_response({"ok": True, "result": result})


@pytest.fixture
async def telegram(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[FakeTelegram]:
    fake = FakeTelegram()
    app = web.Application()
    app.router.add_route("*", "/bot{token}/{method}", fake.handle)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()

    port = site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
    monkeypatch.setattr(
        TELEGRAM_API, "url", f"http://127.0.0.1:{port}/bot{{token}}/{{method}}"
    )

    yield fake
    await runner.cleanup()


def message_update(text: str) -> dict[str, Any]:
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 5,
            "chat": {"id": 7, "type": "private", "first_name": "Вася"},
            "from": {"id": 7, "is_bot": False, "first_name": "Вася"},
            "text": text,
        },
    }


@pytest.fixture
def send(telegram: FakeTelegram, monkeypatch: pytest.MonkeyPatch):
    """Прогнать сообщение с текстом через диспетчер порта; вернуть тексты ответов."""
    # DialogService читает dialogs.json из текущей папки
    monkeypatch.chdir(os.path.dirname(os.path.dirname(__file__)))

    from src.selfrot_bot.__main__ import Dispatcher

    dp = Dispatcher(token="1:TEST")

    async def _send(text: str) -> list[str]:
        telegram.calls.clear()
        update = TypeAdapter(Update).validate_python(
            message_update(text), context={"bot": dp.api}
        )
        await dp._handle(dp.create_context(update))
        return telegram.sent

    _send.dispatcher = dp  # type: ignore[attr-defined]
    return _send
