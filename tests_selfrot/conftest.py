"""
Тесты порта на selfrotgram. Лежат отдельно от tests/: тот conftest автоматически
поднимает Docker с Postgres для КАЖДОГО теста, а часть тестов порта БД не нужна.
Telegram здесь фейковый (HTTP-сервер на localhost), настоящий токен не используется.
Postgres настоящий (Docker, случайный порт), поднимается один раз на запуск.
"""

import json
import os
import time
from collections.abc import AsyncIterator, Callable, Awaitable, Iterator
from typing import Any

import docker
import psycopg
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

from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from selfrot.client.telegram import TELEGRAM_API  # noqa: E402
from selfrot.types import ChatMemberAdministrator, Update  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))


class FakeTelegram:
    """Записывает вызовы Bot API и отвечает заготовками (results — свои ответы)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.results: dict[str, Any] = {}

    @property
    def sent(self) -> list[str]:
        """Тексты всех sendMessage."""
        return [b["text"] for m, b in self.calls if m == "sendMessage"]

    def bodies(self, method: str) -> list[dict[str, Any]]:
        return [b for m, b in self.calls if m == method]

    async def handle(self, request: web.Request) -> web.Response:
        method = request.match_info["method"]
        self.calls.append((method, json.loads(await request.text() or "{}")))

        default: Any = {
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
        return web.json_response(
            {"ok": True, "result": self.results.get(method, default)}
        )


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


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    client = docker.from_env()
    container = client.containers.run(
        "postgres:16-alpine",
        ports={"5432/tcp": None},  # случайный порт: не пересекается с tests/
        environment={
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
            "POSTGRES_DB": "test_db",
        },
        detach=True,
        remove=True,
    )
    try:
        container.reload()
        port = container.ports["5432/tcp"][0]["HostPort"]

        deadline = time.monotonic() + 60
        while True:
            try:
                psycopg.connect(
                    f"postgresql://test:test@127.0.0.1:{port}/test_db"
                ).close()
                break
            except psycopg.OperationalError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.3)

        yield f"postgresql+psycopg://test:test@127.0.0.1:{port}/test_db"
    finally:
        container.stop()


@pytest.fixture
async def session_factory(
    postgres_url: str,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    from src.database.models import Base

    engine = create_async_engine(postgres_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def chat_dict(chat_id: int) -> dict[str, Any]:
    if chat_id < 0:
        return {"id": chat_id, "type": "supergroup", "title": "группа"}
    return {"id": chat_id, "type": "private", "first_name": "Вася"}


def user_dict(uid: int, first_name: str) -> dict[str, Any]:
    return {"id": uid, "is_bot": False, "first_name": first_name}


def message_update(
    text: str, uid: int = 7, first_name: str = "Вася", chat: int | None = None
) -> dict[str, Any]:
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 5,
            "chat": chat_dict(chat if chat is not None else uid),
            "from": user_dict(uid, first_name),
            "text": text,
        },
    }


def callback_update(data: str, uid: int = 7) -> dict[str, Any]:
    return {
        "update_id": 1,
        "callback_query": {
            "id": "cq1",
            "from": user_dict(uid, "Вася"),
            "chat_instance": "ci",
            "data": data,
            "message": {
                "message_id": 44,
                "date": 5,
                "chat": chat_dict(uid),
                "text": "кнопки",
            },
        },
    }


def admin_dict(uid: int) -> dict[str, Any]:
    """Администратор без прав: все обязательные флаги False."""
    flags = {
        name: False
        for name, field in ChatMemberAdministrator.model_fields.items()
        if field.is_required() and name not in ("status", "user")
    }
    return {"status": "administrator", "user": user_dict(uid, "Админ"), **flags}


def owner_dict(uid: int) -> dict[str, Any]:
    return {
        "status": "creator",
        "user": user_dict(uid, "Владелец"),
        "is_anonymous": False,
    }


@pytest.fixture
async def dispatcher(
    telegram: FakeTelegram, session_factory, monkeypatch: pytest.MonkeyPatch
):
    # DialogService читает dialogs.json из текущей папки
    monkeypatch.chdir(REPO_ROOT)

    from src.selfrot_bot.__main__ import Dispatcher

    dp = Dispatcher(token="1:TEST", session_factory=session_factory)
    yield dp
    await dp.api.close_session()


@pytest.fixture
def feed(dispatcher, telegram: FakeTelegram) -> Callable[..., Awaitable[FakeTelegram]]:
    """Прогнать сырой апдейт через диспетчер порта (можно свой диспетчер)."""

    async def _feed(raw: dict[str, Any], dp=None) -> FakeTelegram:
        dp = dp or dispatcher
        telegram.calls.clear()
        update = TypeAdapter(Update).validate_python(raw, context={"bot": dp.api})
        await dp._handle(dp.create_context(update))
        return telegram

    return _feed


@pytest.fixture
def send(feed, dispatcher):
    """Отправить сообщение с текстом; вернуть тексты ответов бота."""

    async def _send(text: str, **kwargs: Any) -> list[str]:
        return (await feed(message_update(text, **kwargs))).sent

    _send.dispatcher = dispatcher  # type: ignore[attr-defined]
    return _send
