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
from aiohttp.web_request import FileField
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

from selfrot.client.telegram import TELEGRAM_API, TELEGRAM_FILE_API  # noqa: E402
from selfrot.types import ChatMemberAdministrator, Update  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(__file__))

# Ошибки приложения, которые тесты вызывают намеренно (ответ на них даёт on_error)
from src.selfrot_bot.__main__ import Dispatcher  # noqa: E402
from src.selfrot_bot.context import AppContext  # noqa: E402
from src.bot.exceptions import (  # noqa: E402
    ChatNotFoundInDatabase,
    RpCommandValidateError,
    UserNotFound,
)

EXPECTED_ERRORS: tuple[type[Exception], ...] = (
    ChatNotFoundInDatabase,
    RpCommandValidateError,
    UserNotFound,
)


def _form_value(value: str | bytes | FileField) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, FileField):
        return f"<file:{value.filename}>"

    return "<bytes>"


class FakeTelegram:
    """Записывает вызовы Bot API и отвечает заготовками (results — свои ответы)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.results: dict[str, Any] = {}
        self.errors: dict[str, tuple[int, str]] = {}  # метод -> (код, описание)
        self._files: dict[str, bytes] = {}  # file_path -> содержимое, для ctx.download
        self.downloads: list[str] = []  # file_path каждого запроса на скачивание
        # метод -> (поле, значение, код, описание): следующий вызов метода с этим
        # значением поля падает этой ошибкой один раз, дальше — как обычно. Для
        # тестов кэша устаревшего telegram_file_id (первая попытка с ним падает,
        # повторная — с диска — проходит).
        self._fail_once: dict[str, tuple[str, str, int, str]] = {}

    def fail_next(
        self,
        method: str,
        field: str,
        value: str,
        code: int = 400,
        description: str = "Bad Request: wrong file identifier/HTTP URL specified",
    ) -> None:
        self._fail_once[method] = (field, value, code, description)

    @property
    def sent(self) -> list[str]:
        """Тексты всех sendMessage."""
        return [b["text"] for m, b in self.calls if m == "sendMessage"]

    def methods_called(self, method: str) -> int:
        return len(self.bodies(method))

    def bodies(self, method: str) -> list[dict[str, Any]]:
        return [b for m, b in self.calls if m == method]

    def set_file(self, file_path: str, content: bytes) -> None:
        """Что отдавать на скачивание file_path (getFile → тот же file_path)."""
        self._files[file_path] = content

    async def handle_file(self, request: web.Request) -> web.Response:
        file_path = request.match_info["file_path"]
        self.downloads.append(file_path)
        content = self._files.get(file_path)
        if content is None:
            return web.Response(status=404, text="Not Found")

        return web.Response(body=content)

    async def handle(self, request: web.Request) -> web.Response:
        method = request.match_info["method"]
        if request.content_type.startswith("multipart/"):
            # файлы загружаются multipart'ом: вместо содержимого пишем имя файла
            form = await request.post()
            body: dict[str, Any] = {k: _form_value(v) for k, v in form.items()}
        else:
            body = json.loads(await request.text() or "{}")
        self.calls.append((method, body))

        once = self._fail_once.get(method)
        if once is not None:
            field, value, code, description = once
            if body.get(field) == value:
                del self._fail_once[method]
                return web.json_response(
                    {"ok": False, "error_code": code, "description": description},
                    status=code,
                )

        if method in self.errors:
            code, description = self.errors[method]
            return web.json_response(
                {"ok": False, "error_code": code, "description": description},
                status=code,
            )

        default: Any = {
            "getMe": {
                "id": 1,
                "is_bot": True,
                "first_name": "B",
                "username": "dev_bot",
            },
            "deleteMessage": True,
            "answerCallbackQuery": True,
            "deleteWebhook": True,
            "setWebhook": True,
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
    app.router.add_route("*", "/file/bot{token}/{file_path:.*}", fake.handle_file)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()

    port = runner.addresses[0][1]
    monkeypatch.setattr(
        TELEGRAM_API, "url", f"http://127.0.0.1:{port}/bot{{token}}/{{method}}"
    )
    monkeypatch.setattr(
        TELEGRAM_FILE_API,
        "url",
        f"http://127.0.0.1:{port}/file/bot{{token}}/{{file_path}}",
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
        bindings = container.ports["5432/tcp"]
        assert bindings, "Docker не пробросил порт Postgres"
        port = bindings[0]["HostPort"]

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
    text: str | None,
    uid: int = 7,
    first_name: str = "Вася",
    chat: int | None = None,
    reply_to_uid: int | None = None,
    reply_to_name: str = "Петя",
    reply_extra: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    chat_id = chat if chat is not None else uid
    message: dict[str, Any] = {
        "message_id": 1,
        "date": 5,
        "chat": chat_dict(chat_id),
        "from": user_dict(uid, first_name),
        **extra,
    }
    if text is not None:
        message["text"] = text

    if reply_to_uid is not None:
        # reply_extra: медиа-сообщение (animation/video/...) вместо текста по умолчанию
        message["reply_to_message"] = {
            "message_id": 0,
            "date": 4,
            "chat": chat_dict(chat_id),
            "from": user_dict(reply_to_uid, reply_to_name),
            **(reply_extra or {"text": "исходное"}),
        }

    return {"update_id": 1, "message": message}


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


def member_dict(status: str, uid: int, first_name: str = "Вася") -> dict[str, Any]:
    """ChatMemberMember/Left/Banned — минимум полей, каких хватает для этого статуса."""
    body: dict[str, Any] = {"status": status, "user": user_dict(uid, first_name)}
    if status == "kicked":
        body["until_date"] = 0
    return body


def chat_member_update(
    uid: int,
    chat: int,
    old_status: str,
    new_status: str,
    first_name: str = "Вася",
    my_chat_member: bool = False,
) -> dict[str, Any]:
    payload = {
        "chat": chat_dict(chat),
        "from": user_dict(uid, first_name),
        "date": 5,
        "old_chat_member": member_dict(old_status, uid, first_name),
        "new_chat_member": member_dict(new_status, uid, first_name),
    }
    field = "my_chat_member" if my_chat_member else "chat_member"
    return {"update_id": 1, field: payload}


class RecordingDispatcher(Dispatcher):
    """
    Dispatcher, который запоминает ошибки, дошедшие до on_error. Сам on_error тихо
    отвечает пользователю текстом, поэтому упавший хендлер легко принять за успешный:
    записанные ошибки тесты проверяют после себя.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.errors: list[Exception] = []

    async def on_error(self, ctx: AppContext, exc: Exception) -> None:
        self.errors.append(exc)
        await super().on_error(ctx, exc)


@pytest.fixture
async def dispatcher(
    telegram: FakeTelegram, session_factory, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[RecordingDispatcher]:
    # DialogService читает dialogs.json из текущей папки
    monkeypatch.chdir(REPO_ROOT)

    dp = RecordingDispatcher(token="1:TEST", session_factory=session_factory)

    yield dp
    # after_handle и defer живут в фоне: не оставляем их работать после теста
    await dp._background.drain(1)
    await dp.api.close_session()

    unexpected = [e for e in dp.errors if not isinstance(e, EXPECTED_ERRORS)]
    assert not unexpected, f"хендлеры упали с неожиданными ошибками: {unexpected!r}"


@pytest.fixture
def feed(
    dispatcher: RecordingDispatcher, telegram: FakeTelegram
) -> Callable[..., Awaitable[FakeTelegram]]:
    """Прогнать сырой апдейт через диспетчер порта (можно свой диспетчер)."""

    async def _feed(raw: dict[str, Any], dp: Dispatcher | None = None) -> FakeTelegram:
        dp = dp or dispatcher
        telegram.calls.clear()
        update = TypeAdapter(Update).validate_python(raw, context={"bot": dp.api})
        await dp._handle(dp.create_context(update))
        return telegram

    return _feed


class Sender:
    """Отправить сообщение с текстом; вернуть тексты ответов бота."""

    def __init__(
        self,
        feed: Callable[..., Awaitable[FakeTelegram]],
        dispatcher: RecordingDispatcher,
    ) -> None:
        self.feed = feed
        self.dispatcher = dispatcher

    async def __call__(self, text: str, **kwargs: Any) -> list[str]:
        return (await self.feed(message_update(text, **kwargs))).sent


@pytest.fixture
def send(feed: Callable[..., Awaitable[FakeTelegram]], dispatcher: RecordingDispatcher):
    return Sender(feed, dispatcher)


def button_data(body: dict[str, Any], label: str) -> str:
    """callback_data кнопки с этим текстом из reply_markup отправленного сообщения."""
    markup = body["reply_markup"]
    if isinstance(markup, str):  # multipart присылает объекты JSON-строкой
        markup = json.loads(markup)

    for row in markup["inline_keyboard"]:
        for button in row:
            if button["text"] == label:
                return button["callback_data"]

    raise AssertionError(f"нет кнопки {label!r} в {markup}")


@pytest.fixture
def settle(dispatcher):
    """Дождаться фоновой работы хендлеров (after_handle). Спящие defer-таймеры
    drain отменяет, их ждут по времени."""

    async def _settle(timeout: float = 5.0) -> None:
        await dispatcher._background.drain(timeout)

    return _settle
