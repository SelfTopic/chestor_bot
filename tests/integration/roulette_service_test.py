from pathlib import Path

import pytest
from sqlalchemy import func, select

from src.bot.exceptions import (
    RouletteBetOutOfRange,
    RouletteBusy,
    RouletteNoChoice,
    RouletteNoMachine,
    RouletteNotEnoughMoney,
    RouletteNotYours,
)
from src.bot.game_configs import LOTTERY_CONFIG
from src.bot.repositories import RouletteRepository, UserRepository, WalletRepository
from src.bot.services.arcade.media import Picture, StoredPicture, StoredVideo, VideoFile
from src.bot.services.roulette import Choice, RouletteService, Stage
from src.bot.services.roulette.positions import color_of, positions_of
from src.bot.services.roulette.spin_video import LANDED_SECONDS
from src.bot.types.dep import DepColor
from src.database.models import Lottery, RouletteMachine
from tests.roulette_fakes import START, FakeScreen, FakeTime, ScriptedRandom, eventually, fake_render, make_videos

CHAT = -1001
PLAYER, OTHER = 700001, 700002
FLIGHT = LANDED_SECONDS + LOTTERY_CONFIG.playback_delay_seconds


class FakeUploader:
    def __init__(self) -> None:
        self.pictures = 0

    async def video(self, path: Path) -> str:
        return f"video:{path.name}"

    async def picture(self, png: bytes) -> str:
        self.pictures += 1
        return f"picture:{self.pictures}"


@pytest.fixture
async def roulette(session_factory, tmp_path):
    videos = make_videos(session_factory, tmp_path)
    clock = FakeTime()
    rng = ScriptedRandom()
    service = RouletteService(session_factory, videos, clock=clock.clock, sleep=clock.sleep, rng=rng)
    service.screen = screen = FakeScreen()
    async with session_factory() as session:
        for telegram_id in (PLAYER, OTHER):
            await UserRepository(session).upsert(telegram_id=telegram_id, first_name="P")
            await WalletRepository(session).change(telegram_id, 10_000)
        await session.commit()
    await service.start()
    yield service, clock, screen, rng, tmp_path
    await service.close()


async def balance(session_factory, telegram_id: int) -> int | None:
    async with session_factory() as session:
        return await WalletRepository(session).balance(telegram_id)


def ready_video(tmp_path: Path, start: int, end: int) -> None:
    fake_render(start, end, tmp_path / f"{start}-{end}.mp4")


async def test_spin_plays_the_video_then_lands_with_the_old_lottery_payout(roulette, session_factory):
    service, clock, screen, rng, tmp_path = roulette
    end = positions_of(DepColor.RED)[-1]
    ready_video(tmp_path, START, end)

    await service.open(CHAT, PLAYER, DepColor.RED, 1000)
    opened = screen.last
    assert opened.stage is Stage.READY and opened.message_id is None
    assert opened.media == Picture(f"rest:{START}".encode())
    assert opened.choice == Choice(DepColor.RED, 1000) and opened.balance == 10_000

    await service.spin(opened.machine_id, PLAYER)
    spinning = screen.last
    assert spinning.stage is Stage.SPINNING and spinning.message_id == 42
    assert isinstance(spinning.media, VideoFile)
    assert spinning.media.path == tmp_path / f"{START}-{end}.mp4"
    # Выигрыш ×1.8 сверх ставки, как у прежней лотереи.
    assert await balance(session_factory, PLAYER) == 11_800

    await clock.advance(FLIGHT)
    await eventually(lambda: screen.last.stage is Stage.READY)
    landed = screen.last
    assert landed.media == Picture(f"rest:{end}".encode())
    assert landed.outcome is not None
    assert (landed.outcome.winning, landed.outcome.earned, landed.outcome.balance) == (
        DepColor.RED,
        1800,
        11_800,
    )
    assert service._machines[opened.machine_id].position == end

    async with session_factory() as session:
        machine = await session.get(RouletteMachine, opened.machine_id)
        assert machine is not None and machine.position == end and machine.message_id == 42
        lottery = await session.scalar(select(Lottery))
        assert lottery is not None and (lottery.is_won, lottery.earned) == (True, 1800)


async def test_next_spin_starts_where_the_ribbon_stopped_and_loses_the_bet(roulette, session_factory):
    service, clock, screen, rng, tmp_path = roulette
    first = positions_of(DepColor.RED)[-1]
    second = positions_of(DepColor.WHITE)[-1]
    ready_video(tmp_path, START, first)
    ready_video(tmp_path, first, second)
    await service.open(CHAT, PLAYER, DepColor.RED, 1000)
    machine_id = screen.last.machine_id
    await service.spin(machine_id, PLAYER)
    await clock.advance(FLIGHT)
    await eventually(lambda: screen.last.stage is Stage.READY)

    rng.winning = DepColor.WHITE
    await service.spin(machine_id, PLAYER)
    spinning = screen.last.media
    assert isinstance(spinning, VideoFile) and spinning.path.name == f"{first}-{second}.mp4"
    await clock.advance(FLIGHT)
    await eventually(lambda: screen.last.stage is Stage.READY)
    outcome = screen.last.outcome
    assert outcome is not None and (outcome.winning, outcome.earned) == (DepColor.WHITE, -1000)
    assert await balance(session_factory, PLAYER) == 10_800


async def test_spin_needs_a_full_choice_and_remembers_it(roulette, session_factory):
    service, clock, screen, rng, tmp_path = roulette
    await service.open(CHAT, PLAYER)
    machine_id = screen.last.machine_id
    with pytest.raises(RouletteNoChoice):
        await service.spin(machine_id, PLAYER)

    await service.choose(machine_id, PLAYER, color=DepColor.BLUE)
    assert screen.last.choice == Choice(DepColor.BLUE, None)
    assert await service.choose(machine_id, PLAYER, amount=500) == Choice(DepColor.BLUE, 500)
    with pytest.raises(RouletteBetOutOfRange):
        await service.choose(machine_id, PLAYER, amount=LOTTERY_CONFIG.max_bet + 1)

    rng.winning = DepColor.BLUE
    await service.spin(machine_id, PLAYER)
    # Ролика ещё нет: лента встаёт сразу, а ролик рендерится вне очереди.
    landed = screen.last
    assert landed.stage is Stage.READY and landed.choice == Choice(DepColor.BLUE, 500)
    assert landed.outcome is not None and landed.outcome.earned == 1250
    await service._videos.idle()
    assert (tmp_path / f"{START}-{positions_of(DepColor.BLUE)[-1]}.mp4").exists()


async def test_machine_is_personal_and_busy_while_spinning(roulette, session_factory):
    service, clock, screen, rng, tmp_path = roulette
    ready_video(tmp_path, START, positions_of(DepColor.RED)[-1])
    await service.open(CHAT, PLAYER, DepColor.RED, 1000)
    machine_id = screen.last.machine_id

    with pytest.raises(RouletteNotYours):
        await service.spin(machine_id, OTHER)
    await service.spin(machine_id, PLAYER)
    with pytest.raises(RouletteBusy):
        await service.spin(machine_id, PLAYER)
    with pytest.raises(RouletteBusy):
        await service.open(CHAT, PLAYER)
    # Новая ставка во время прокрута не трогает ролик, а приходит вместе с итогом.
    shown = len(screen.screens)
    await service.choose(machine_id, PLAYER, amount=5000)
    assert len(screen.screens) == shown
    await clock.advance(FLIGHT)
    await eventually(lambda: screen.last.stage is Stage.READY)
    assert screen.last.choice == Choice(DepColor.RED, 5000)
    assert await balance(session_factory, PLAYER) == 11_800


async def test_not_enough_money_keeps_the_machine_ready(roulette, session_factory):
    service, clock, screen, rng, tmp_path = roulette
    await service.open(CHAT, PLAYER, DepColor.RED, LOTTERY_CONFIG.max_bet)
    machine_id = screen.last.machine_id
    with pytest.raises(RouletteNotEnoughMoney):
        await service.spin(machine_id, PLAYER)
    assert not service._machines[machine_id].spinning
    assert await balance(session_factory, PLAYER) == 10_000
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Lottery)) == 0


async def test_machine_closes_after_idle_time(roulette, session_factory):
    service, clock, screen, rng, tmp_path = roulette
    await service.open(CHAT, PLAYER)
    machine_id = screen.last.machine_id

    await clock.advance(LOTTERY_CONFIG.idle_seconds - 10)
    await service.choose(machine_id, PLAYER, color=DepColor.GREEN)
    await clock.advance(20)
    assert screen.last.stage is Stage.READY

    await clock.advance(LOTTERY_CONFIG.idle_seconds)
    await eventually(lambda: screen.last.stage is Stage.CLOSED)
    assert screen.last.media == Picture(f"closed:{START}".encode())
    with pytest.raises(RouletteNoMachine):
        await service.spin(machine_id, PLAYER)
    async with session_factory() as session:
        assert await RouletteRepository(session).open_machines() == []


async def test_reopening_moves_the_machine_down_with_its_ribbon_and_bet(roulette, session_factory):
    service, clock, screen, rng, tmp_path = roulette
    await service.open(CHAT, PLAYER, DepColor.YELLOW, 2000)
    old = screen.last.machine_id
    await service.spin(old, PLAYER)
    position = service._machines[old].position
    assert color_of(position) is DepColor.RED

    await service.open(CHAT, PLAYER, amount=3000)
    closed, opened = screen.screens[-2:]
    assert (closed.stage, closed.machine_id) == (Stage.CLOSED, old)
    assert opened.stage is Stage.READY and opened.machine_id != old
    assert opened.message_id is None
    assert opened.media == Picture(f"rest:{position}".encode())
    assert opened.choice == Choice(DepColor.YELLOW, 3000)

    await service.open(CHAT, OTHER)
    async with session_factory() as session:
        assert len(await RouletteRepository(session).open_machines()) == 2


async def test_stale_file_ids_are_uploaded_again(roulette, session_factory):
    service, clock, screen, rng, tmp_path = roulette
    service._videos.uploader = FakeUploader()
    end = positions_of(DepColor.RED)[-1]
    ready_video(tmp_path, START, end)
    await service._videos._cache.upload(tmp_path / f"{START}-{end}.mp4")

    screen.stale_once = True
    await service.open(CHAT, PLAYER, DepColor.RED, 100)
    stale, fresh = screen.screens[-2:]
    assert isinstance(stale.media, StoredPicture)
    assert fresh.media == Picture(f"rest:{START}".encode())

    screen.stale_once = True
    await service.spin(fresh.machine_id, PLAYER)
    stale, fresh = screen.screens[-2:]
    assert isinstance(stale.media, StoredVideo) and isinstance(fresh.media, VideoFile)
    assert await service._videos.spin(START, end) == StoredVideo(fresh.media.key, "uploaded")


async def test_restart_closes_machines_left_open(session_factory, tmp_path):
    async with session_factory() as session:
        await UserRepository(session).upsert(telegram_id=PLAYER, first_name="P")
        repository = RouletteRepository(session)
        machine_id = await repository.open_machine(CHAT, PLAYER, 7)
        assert machine_id is not None
        await repository.set_message(machine_id, 99)
        await session.commit()

    service = RouletteService(session_factory, make_videos(session_factory, tmp_path))
    service.screen = screen = FakeScreen()
    await service.start()
    await service.close()

    (closed,) = screen.screens
    assert (closed.stage, closed.message_id, closed.media) == (
        Stage.CLOSED,
        99,
        Picture(b"closed:7"),
    )
    async with session_factory() as session:
        assert await RouletteRepository(session).open_machines() == []
