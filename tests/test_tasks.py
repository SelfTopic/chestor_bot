"""Фоновые задачи (Dispatcher.tasks) идут через те же middleware, что и апдейты: сессия БД,
сервисы. Каждая задача из TASKS проходит один прогон на пустой базе без ошибок и без вызовов
Telegram — так видно, что связка ctx, сессии и сервисов у задачи цела. Что именно делает
задача, проверяют тесты её области (дуэли, браки, уведомления, модерация, статистика)."""

import pytest

from src.bot.tasks import TASKS


@pytest.mark.parametrize("every", TASKS, ids=lambda every: every.task_cls.__name__)
async def test_every_task_runs_on_an_empty_database(dispatcher, telegram, every):
    telegram.calls.clear()

    await dispatcher.run_task(every.task_cls)

    assert dispatcher.errors == []
    assert telegram.calls == []
