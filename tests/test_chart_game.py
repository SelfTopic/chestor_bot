import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest

from src.bot.dialogs import Dialogs
from src.bot.game_configs import CHART_CONFIG
from src.bot.repositories import WalletRepository
from src.bot.routers import TelegramMachineScreen
from src.bot.routers.arcade.chart.payloads import CashOutPress
from src.bot.services.chart_game import ChartGameService, ChartVideos
from tests.chart_fakes import FakeTime, FixedRandom, fake_render
from tests.conftest import (
    button_data,
    callback_update,
    chat_dict,
    message_update,
    only_text,
    owner_dict,
    phrase_texts,
    rich_texts,
)

CHART = Dialogs.chart
CHAT = -1001234567890
PLAYER = 700001


def rich_body(body: dict[str, Any]) -> dict[str, Any]:
    # С файлами внутри запрос идёт multipart: объекты приходят JSON-строкой.
    return {
        key: json.loads(value) if key in ("rich_message", "reply_markup") and isinstance(value, str) else value
        for key, value in body.items()
    }


def press(data: str) -> dict[str, Any]:
    update = callback_update(data, uid=PLAYER)
    update["callback_query"]["message"]["chat"] = chat_dict(CHAT)
    return update


@pytest.fixture
async def chart(dispatcher, telegram, session_factory, tmp_path):
    telegram.results["getChatAdministrators"] = [owner_dict(99)]
    growth = tmp_path / "growth.mp4"
    growth.write_bytes(b"growth")
    videos = ChartVideos(
        session_factory,
        growth=growth,
        crash_path=lambda crash: tmp_path / "crash" / f"{crash}.mp4",
        render=fake_render,
        executor=lambda: ThreadPoolExecutor(1),
        warm=(),
    )
    clock = FakeTime()
    service = ChartGameService(
        session_factory, videos, clock=clock.clock, sleep=clock.sleep, rng=FixedRandom(0.5)
    )
    service.screen = TelegramMachineScreen(dispatcher.api, session_factory, dispatcher.dialog_service)
    dispatcher.chart_service = service
    await service.start()
    yield service, clock, growth
    await service.close()


async def open_machine(feed, telegram, chart, session_factory, money: int = 10_000):
    service, clock, _ = chart
    await feed(message_update("джет", uid=PLAYER, chat=CHAT))
    await clock.until_blocked(service)
    async with session_factory() as session:
        await WalletRepository(session).change(PLAYER, money)
        await session.commit()
    (body,) = telegram.bodies("sendRichMessage")
    return rich_body(body)


async def popup(feed, data: str) -> str:
    telegram = await feed(press(data))
    (answer,) = telegram.bodies("answerCallbackQuery")
    return answer["text"]


def growth_at(started: float, multiplier: float) -> float:
    growth = started + CHART_CONFIG.until_growth_seconds
    return growth + CHART_CONFIG.seconds_to(multiplier) + 0.001


async def test_round_through_buttons(feed, telegram, chart, session_factory):
    service, clock, _ = chart
    started = clock.now
    opened = await open_machine(feed, telegram, chart, session_factory)
    assert only_text(CHART.preparation(minutes=5)) in rich_texts(opened)

    bet = button_data(opened, only_text(CHART.amount_button(amount="1.000")))
    assert await popup(feed, bet) == only_text(CHART.bet_placed(amount="1.000"))
    assert await popup(feed, bet) == only_text(CHART.already_bet())
    target = button_data(opened, only_text(CHART.target_button(target="3")))
    assert await popup(feed, target) == only_text(CHART.target_set(target="3"))

    telegram.calls.clear()
    await clock.advance_to(started + CHART_CONFIG.preparation_seconds, service)
    (growing,) = map(rich_body, telegram.bodies("editMessageText"))
    cash_out = button_data(growing, only_text(CHART.cash_out_button()))
    assert await popup(feed, cash_out) == only_text(CHART.not_growing())

    await clock.advance_to(growth_at(started, 1.5), service)
    assert await popup(feed, cash_out) == only_text(CHART.cashed(multiplier="1.50", payout="1.500"))
    async with session_factory() as session:
        assert await WalletRepository(session).balance(PLAYER) == 10_500

    telegram.calls.clear()
    await clock.advance_to(growth_at(started, 1.92), service)
    (crashed,) = map(rich_body, telegram.bodies("editMessageText"))
    texts = rich_texts(crashed)
    assert only_text(CHART.crashed(crash="1.92")) in "\n".join(texts)
    assert only_text(CHART.won_line(name="Вася", multiplier="1.50", payout="1.500")) in texts
    assert await popup(feed, cash_out) == only_text(CHART.already_cashed(multiplier="1.50"))


async def test_not_enough_money_for_bet(feed, telegram, chart, session_factory):
    opened = await open_machine(feed, telegram, chart, session_factory, money=500)

    bet = button_data(opened, only_text(CHART.amount_button(amount="1.000")))

    assert await popup(feed, bet) == only_text(CHART.not_enough_money())


async def test_second_machine_links_to_the_running_one(feed, telegram, chart, session_factory):
    await open_machine(feed, telegram, chart, session_factory)

    await feed(message_update("джет", uid=PLAYER, chat=CHAT))

    (reply,) = telegram.bodies("sendMessage")
    assert reply["text"] in phrase_texts(CHART.already_open_link(link="https://t.me/c/1234567890/100"))
    assert reply["parse_mode"] == "HTML"


async def test_second_machine_in_private_chat_has_no_link(chart, send):
    service, clock, _ = chart
    await send("джет", uid=PLAYER)
    await clock.until_blocked(service)

    (reply,) = await send("джет", uid=PLAYER)

    assert reply in phrase_texts(CHART.already_open())


async def test_press_on_closed_machine(feed, chart):
    assert await popup(feed, CashOutPress().pack()) == only_text(CHART.machine_closed())


async def test_no_machine_without_growth_video(chart, send):
    _, _, growth = chart
    growth.unlink()

    (reply,) = await send("джет", uid=PLAYER, chat=CHAT)

    assert reply == only_text(CHART.unavailable())
