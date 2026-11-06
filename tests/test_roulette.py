import json
from typing import Any

import pytest

from src.bot.dialogs import Dialogs
from src.bot.game_configs import LOTTERY_CONFIG
from src.bot.repositories import WalletRepository
from src.bot.routers import TelegramRouletteScreen
from src.bot.services.roulette import Clip, RouletteService
from src.bot.services.roulette.positions import positions_of
from src.bot.services.roulette.spin_video import LANDED_SECONDS
from src.bot.types.dep import DepColor
from tests.conftest import (
    button_data,
    callback_update,
    chat_dict,
    matches_phrase,
    message_update,
    only_text,
    owner_dict,
    phrase_texts,
    rich_texts,
)
from tests.roulette_fakes import (
    START,
    FakeTime,
    ScriptedRandom,
    clip_path,
    eventually,
    fake_render,
    make_videos,
)

ROULETTE = Dialogs.roulette
CHAT = -1001234567890
PLAYER, OTHER = 700001, 700002
FLIGHT = LANDED_SECONDS + LOTTERY_CONFIG.playback_delay_seconds
RED = only_text(Dialogs.vocab.color.red())


def rich_body(body: dict[str, Any]) -> dict[str, Any]:
    # С файлами внутри запрос идёт multipart: объекты приходят JSON-строкой.
    return {
        key: json.loads(value) if key in ("rich_message", "reply_markup") and isinstance(value, str) else value
        for key, value in body.items()
    }


def press(data: str, uid: int = PLAYER) -> dict[str, Any]:
    update = callback_update(data, uid=uid)
    update["callback_query"]["message"]["chat"] = chat_dict(CHAT)
    return update


def buttons(body: dict[str, Any]) -> list[dict[str, Any]]:
    return [button for row in body["reply_markup"]["inline_keyboard"] for button in row]


@pytest.fixture
async def roulette(dispatcher, telegram, session_factory, tmp_path):
    telegram.results["getChatAdministrators"] = [owner_dict(99)]
    clock = FakeTime()
    rng = ScriptedRandom()
    service = RouletteService(
        session_factory, make_videos(session_factory, tmp_path), clock=clock.clock, sleep=clock.sleep, rng=rng
    )
    service.screen = TelegramRouletteScreen(dispatcher.api, session_factory, dispatcher.dialog_service)
    dispatcher.roulette_service = service
    await service.start()
    yield service, clock, rng, tmp_path
    await service.close()


async def open_machine(feed, telegram, session_factory, text: str = "депнуть") -> dict[str, Any]:
    await feed(message_update(text, uid=PLAYER, chat=CHAT))
    (body,) = telegram.bodies("sendRichMessage")
    return rich_body(body)


async def fund(session_factory, amount: int = 10_000) -> None:
    async with session_factory() as session:
        await WalletRepository(session).change(PLAYER, amount)
        await session.commit()


async def alert(feed, data: str, uid: int = PLAYER) -> str:
    telegram = await feed(press(data, uid))
    (answer,) = telegram.bodies("answerCallbackQuery")
    assert answer["show_alert"] is True
    return answer["text"]


async def test_machine_through_buttons(feed, telegram, roulette, session_factory):
    service, clock, rng, tmp_path = roulette
    opened = await open_machine(feed, telegram, session_factory)
    assert only_text(ROULETTE.choose()) in rich_texts(opened)[0].split("\n")
    red = next(b for b in buttons(opened) if b["text"].startswith("🔴"))
    assert red["style"] == "danger"
    assert not any("style" in b for b in buttons(opened) if b["text"].startswith("🟡"))

    spin = button_data(opened, only_text(ROULETTE.spin_button()))
    assert await alert(feed, spin) == only_text(ROULETTE.no_choice())
    await fund(session_factory)

    await feed(press(red["callback_data"]))
    amount = button_data(opened, only_text(ROULETTE.amount_button(amount="1.000")))
    await feed(press(amount))
    (chosen,) = map(rich_body, telegram.bodies("editMessageText"))
    choice = only_text(ROULETTE.choice(color=f"🔴 {RED}", multiplier="1.8", amount="1.000"))
    assert choice in rich_texts(chosen)[0].split("\n")
    assert only_text(ROULETTE.amount_button_chosen(amount="1.000")) in [b["text"] for b in buttons(chosen)]

    clip = Clip(START, positions_of(DepColor.RED)[-1], 0)
    fake_render(clip, clip_path(tmp_path, clip))
    await feed(press(spin))
    (spinning,) = map(rich_body, telegram.bodies("editMessageText"))
    assert spinning["rich_message"]["blocks"][0]["type"] == "animation"

    telegram.calls.clear()
    await clock.advance(FLIGHT)
    (landed,) = map(rich_body, telegram.bodies("editMessageText"))
    assert landed["rich_message"]["blocks"][0]["type"] == "photo"
    lines = rich_texts(landed)[0].split("\n")
    assert any(line in phrase_texts(ROULETTE.won(winning=f"🔴 {RED}", earned="1.800")) for line in lines)
    assert only_text(ROULETTE.balance(balance="11.800")) in lines


async def test_preset_opens_with_the_bet(feed, telegram, roulette, session_factory):
    opened = await open_machine(feed, telegram, session_factory, "ставка красный 2500")
    choice = only_text(ROULETTE.choice(color=f"🔴 {RED}", multiplier="1.8", amount="2.500"))
    assert choice in rich_texts(opened)[0].split("\n")


async def test_open_errors(send, roulette):
    (reply,) = await send("депнуть фиолетовый 100", uid=PLAYER)
    assert matches_phrase(reply, "roulette.unknown_color") and "фиолетовый" in reply
    (reply,) = await send("депнуть красный сто", uid=PLAYER)
    assert matches_phrase(reply, "roulette.usage")


async def test_only_the_owner_presses(feed, telegram, roulette, session_factory):
    opened = await open_machine(feed, telegram, session_factory, "депнуть красный 100")
    spin = button_data(opened, only_text(ROULETTE.spin_button()))
    assert await alert(feed, spin, uid=OTHER) == only_text(ROULETTE.not_yours())
    assert await alert(feed, spin) in phrase_texts(ROULETTE.not_enough_money())


async def test_idle_machine_closes(feed, telegram, roulette, session_factory):
    service, clock, rng, tmp_path = roulette
    opened = await open_machine(feed, telegram, session_factory)
    telegram.calls.clear()
    await clock.advance(LOTTERY_CONFIG.idle_seconds)
    await eventually(lambda: bool(telegram.bodies("editMessageText")))
    (closed,) = map(rich_body, telegram.bodies("editMessageText"))
    assert only_text(ROULETTE.closed()) in rich_texts(closed)[0].split("\n")
    assert not closed.get("reply_markup")
    spin = button_data(opened, only_text(ROULETTE.spin_button()))
    assert await alert(feed, spin) == only_text(ROULETTE.machine_closed())
