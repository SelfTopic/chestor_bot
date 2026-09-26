"""Как у прода: ENV=DEV — polling, иначе вебхук; перед любым режимом вебхук снимается."""

import asyncio
import contextlib
import socket
from typing import Any

import aiohttp
import pytest
from pydantic import SecretStr

from src.config import settings
from src.selfrot_bot import __main__ as entry

from .conftest import message_update


@pytest.fixture
def started(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        entry.Dispatcher, "start_polling", lambda self: calls.append(("polling", {}))
    )
    monkeypatch.setattr(
        entry.Dispatcher,
        "start_webhook",
        lambda self, **kwargs: calls.append(("webhook", kwargs)),
    )
    # main() настраивает логи с файлом logs.log в корне репо: тестам режима это не
    # нужно, а настоящий logs.log разработчика ротировался бы при первом warning.
    monkeypatch.setattr(entry, "setup_logging", lambda: None)
    monkeypatch.setattr(settings, "BOT_TOKEN", SecretStr("1:TEST"))
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    return calls


def test_dev_polls(started, monkeypatch):
    monkeypatch.setattr(settings, "ENV", "DEV")

    entry.main()

    assert started == [("polling", {})]


def test_not_dev_uses_webhook(started, monkeypatch):
    monkeypatch.setattr(settings, "ENV", "PROD")
    monkeypatch.setenv("WEBHOOK_URL", "https://chestor.site/webhook/selfrot")
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cret_-")

    entry.main()

    assert started == [
        (
            "webhook",
            {
                "url": "https://chestor.site/webhook/selfrot",
                "secret_token": "s3cret_-",
                "host": "0.0.0.0",
                "port": 8999,
            },
        )
    ]


@pytest.mark.parametrize("missing", ["WEBHOOK_URL", "WEBHOOK_SECRET"])
def test_webhook_without_settings_stops_before_start(started, monkeypatch, missing):
    monkeypatch.setattr(settings, "ENV", "PROD")
    monkeypatch.setenv("WEBHOOK_URL", "https://chestor.site/webhook/selfrot")
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cret")
    monkeypatch.delenv(missing)

    with pytest.raises(SystemExit, match=missing):
        entry.main()
    assert started == []


async def test_startup_drops_old_webhook(dispatcher, telegram):
    await dispatcher.on_startup()
    await dispatcher.on_shutdown()

    assert telegram.bodies("deleteWebhook") == [{"drop_pending_updates": True}]


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


async def test_webhook_mode_serves_updates(dispatcher, telegram):
    """Настоящий вебхук-сервер порта: апдейт с верным секретом обработан, с чужим — 403."""
    port = _free_port()
    serving = asyncio.create_task(
        dispatcher.webhook(
            url="https://chestor.site/webhook/selfrot",
            secret_token="s3cret",
            host="127.0.0.1",
            port=port,
        )
    )
    try:
        for _ in range(100):  # сервер поднимается раньше setWebhook
            if telegram.bodies("setWebhook"):
                break
            await asyncio.sleep(0.05)
        (hook,) = telegram.bodies("setWebhook")
        assert hook["url"] == "https://chestor.site/webhook/selfrot"
        assert hook["secret_token"] == "s3cret"
        assert "chat_member" in hook["allowed_updates"]

        endpoint = f"http://127.0.0.1:{port}/webhook/selfrot"
        async with aiohttp.ClientSession() as http:
            async with http.post(
                endpoint,
                json=message_update("бот"),
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
            ) as denied:
                assert denied.status == 403
            async with http.post(
                endpoint,
                json=message_update("бот"),
                headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"},
            ) as accepted:
                assert accepted.status == 200

        for _ in range(100):
            if telegram.bodies("sendMessage"):
                break
            await asyncio.sleep(0.05)
        assert telegram.bodies("sendMessage"), "бот не ответил на апдейт из вебхука"
    finally:
        serving.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await serving
