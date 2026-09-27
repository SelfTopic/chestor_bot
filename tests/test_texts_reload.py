"""Сломанная правка текстов на ходу: бот отвечает прежними и один раз пишет об этом админам."""

import asyncio
import os

import pytest

from src.bot.dialogs import DIALOGS_DIR, DialogFileError, Dialogs, load_texts
from src.bot.services.dialog import DialogService
from src.config import settings

from .conftest import message_update, only_text

ADMINS = [1001, 1002]


async def test_broken_edit_alerts_admins_once(
    feed, dispatcher, telegram, monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "ADMIN_IDS", ADMINS)
    for path in DIALOGS_DIR.glob("*.yaml"):
        (tmp_path / path.name).write_text(path.read_text("utf-8"), "utf-8")
    dispatcher.dialog_service = DialogService(
        tmp_path, on_broken=dispatcher.report_broken_texts
    )

    edited = tmp_path / "admin.yaml"
    edited.write_text(edited.read_text("utf-8") + "broken: {\n", "utf-8")
    # mtime задаётся явно: копия и правка могут попасть в один тик часов ФС.
    os.utime(edited, (1, 1))
    with pytest.raises(DialogFileError) as broken:
        load_texts(tmp_path)

    await feed(message_update("/start", uid=42))
    await asyncio.gather(*dispatcher.alerts)
    alert = only_text(Dialogs.admin.texts_broken(error=str(broken.value)))
    to_admins = [b for b in telegram.bodies("sendMessage") if b["chat_id"] in ADMINS]
    assert [(b["chat_id"], b["text"]) for b in to_admins] == [(a, alert) for a in ADMINS]

    await feed(message_update("/start", uid=42))
    assert not dispatcher.alerts
    assert not [b for b in telegram.bodies("sendMessage") if b["chat_id"] in ADMINS]
