import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import select

from src.bot.exceptions import (
    ChartMachineOpen,
    ChartNotEnoughMoney,
    ChartStaleVideo,
    ChartTooLate,
    ChartUnavailable,
)
from src.bot.game_configs import CHART_CONFIG
from src.bot.repositories import ChartRepository, UserRepository, WalletRepository
from src.bot.services.chart_game.screen import BetLine, Screen, Shown, Stage
from src.bot.services.chart_game.service import ChartGameService
from src.bot.services.chart_game.videos import (
    ChartVideos,
    Picture,
    StoredPicture,
    WARM,
    StoredVideo,
    VideoFile,
    video_key,
)
from src.database.models import ChartMachine
from tests.chart_fakes import FakeTime, FixedRandom, fake_opening, fake_render

CHAT = -1001
PLAYER, OTHER = 700001, 700002


class FakeScreen:
    def __init__(self) -> None:
        self.screens: list[Screen] = []
        self.stale_once = False

    async def show(self, screen: Screen) -> Shown:
        self.screens.append(screen)
        if self.stale_once and isinstance(screen.media, StoredVideo):
            self.stale_once = False
            raise ChartStaleVideo()
        file_id = "uploaded" if isinstance(screen.media, VideoFile) else None
        return Shown(message_id=42, file_id=file_id)

    async def bets_picture(self, chat_id: int, bets: list[BetLine]) -> bytes:
        return f"panel:{len(bets)}".encode()

    async def closed_picture(self, chat_id: int, crash: int) -> bytes:
        return f"closed:{crash}".encode()


class FakeUploader:
    def __init__(self) -> None:
        self.pictures = 0

    async def video(self, path: Path) -> str:
        return f"video:{path.name}"

    async def picture(self, png: bytes) -> str:
        self.pictures += 1
        return f"picture:{self.pictures}"


def make_videos(session_factory, tmp_path: Path, warm=()) -> ChartVideos:
    growth = tmp_path / "growth.mp4"
    growth.write_bytes(b"growth")
    return ChartVideos(
        session_factory,
        growth=growth,
        opening=tmp_path / "opening.mp4",
        render_opening=fake_opening,
        crash_path=lambda crash: tmp_path / "crash" / f"{crash}.mp4",
        render=fake_render,
        executor=lambda: ThreadPoolExecutor(1),
        warm=warm,
    )


@pytest.fixture
async def game(session_factory, tmp_path):
    videos = make_videos(session_factory, tmp_path)
    clock = FakeTime()
    service = ChartGameService(
        session_factory, videos, clock=clock.clock, sleep=clock.sleep, rng=FixedRandom(0.5)
    )
    service.screen = screen = FakeScreen()
    async with session_factory() as session:
        for telegram_id in (PLAYER, OTHER):
            await UserRepository(session).upsert(telegram_id=telegram_id, first_name="P")
            await WalletRepository(session).change(telegram_id, 10_000)
        await session.commit()
    await service.start()
    yield service, clock, screen, session_factory
    await service.close()


async def balance(session_factory, telegram_id: int) -> int | None:
    async with session_factory() as session:
        return await WalletRepository(session).balance(telegram_id)


def growth_at(started: float, multiplier: float) -> float:
    growth = started + CHART_CONFIG.until_growth_seconds
    return growth + CHART_CONFIG.seconds_to(multiplier) + 0.001


async def test_round_bets_cash_out_crash_and_next_preparation(game):
    service, clock, screen, sessions = game
    started = clock.now
    opening = service._videos._opening
    await service._videos.idle()
    await service.open(CHAT, PLAYER)
    await clock.until_blocked(service)
    assert screen.screens[-1].stage is Stage.PREPARATION
    assert screen.screens[-1].media == VideoFile(video_key(opening), opening)

    await service.bet(CHAT, PLAYER, 1000, None)
    await service.bet(CHAT, OTHER, 1000, None)
    assert await balance(sessions, PLAYER) == 9000

    await clock.advance_to(started + CHART_CONFIG.preparation_seconds, service)
    growth = screen.screens[-1]
    assert growth.stage is Stage.GROWTH and growth.message_id == 42
    assert isinstance(growth.media, VideoFile)
    assert growth.panel == Picture(b"panel:2")

    await clock.advance_to(growth_at(started, 1.5), service)
    cashed = await service.cash_out(CHAT, PLAYER)
    assert (cashed.cashed_at, cashed.payout) == (150, 1500)
    assert await balance(sessions, PLAYER) == 10_500

    await clock.advance_to(growth_at(started, 1.92), service)
    crash = screen.screens[-1]
    assert (crash.stage, crash.crash) == (Stage.PREPARATION, 192)
    assert crash.panel == growth.panel
    assert {line.telegram_id: line.payout for line in crash.bets} == {
        PLAYER: 1500,
        OTHER: 0,
    }
    with pytest.raises(ChartTooLate):
        await service.cash_out(CHAT, OTHER)

    await clock.advance_to(clock.now + CHART_CONFIG.preparation_seconds, service)
    assert isinstance(screen.screens[-1].media, StoredVideo)


async def test_auto_cash_out_pays_at_crash(game):
    service, clock, screen, sessions = game
    started = clock.now
    await service.open(CHAT, PLAYER)
    await clock.until_blocked(service)
    await service.bet(CHAT, PLAYER, 1000, None)
    await service.set_target(CHAT, PLAYER, 150)
    await service.bet(CHAT, OTHER, 1000, 200)

    await clock.advance_to(started + CHART_CONFIG.preparation_seconds, service)
    await clock.advance_to(growth_at(started, 1.92), service)

    assert await balance(sessions, PLAYER) == 10_500
    assert await balance(sessions, OTHER) == 9000
    assert BetLine(PLAYER, 1000, 150, 150, 1500) in screen.screens[-1].bets


async def test_not_enough_money_keeps_player_out(game):
    service, clock, _, sessions = game
    await service.open(CHAT, PLAYER)
    await clock.until_blocked(service)

    with pytest.raises(ChartNotEnoughMoney):
        await service.bet(CHAT, PLAYER, 20_000, None)
    await service.bet(CHAT, PLAYER, 10_000, None)

    assert await balance(sessions, PLAYER) == 0


async def test_one_machine_per_chat(game):
    service, clock, _, _ = game
    await service.open(CHAT, PLAYER)
    await clock.until_blocked(service)

    with pytest.raises(ChartMachineOpen) as error:
        await service.open(CHAT, OTHER)
    assert error.value.message_id == 42


async def test_machine_closes_after_lifetime(game, monkeypatch):
    service, clock, screen, sessions = game
    monkeypatch.setattr(CHART_CONFIG, "machine_lifetime_seconds", 1.0)
    started = clock.now
    await service.open(CHAT, PLAYER)
    await clock.until_blocked(service)

    await clock.advance_to(started + CHART_CONFIG.preparation_seconds, service)
    await clock.advance_to(growth_at(started, 1.92), service)
    await service.idle()

    assert (screen.screens[-1].stage, screen.screens[-1].crash) == (Stage.CLOSED, 192)
    assert screen.screens[-1].media == Picture(b"closed:192")
    assert not service.is_open(CHAT)
    async with sessions() as session:
        closed = await session.scalar(select(ChartMachine.closed_at))
    assert closed is not None


async def test_stale_video_is_uploaded_again(game, tmp_path):
    growth_file = tmp_path / "growth.mp4"
    service, clock, screen, sessions = game
    started = clock.now
    async with sessions() as session:
        await ChartRepository(session).save_video(video_key(growth_file), "stale")
        await session.commit()
    screen.stale_once = True
    await service.open(CHAT, PLAYER)
    await clock.until_blocked(service)

    await clock.advance_to(started + CHART_CONFIG.preparation_seconds, service)

    stale, fresh = screen.screens[-2:]
    assert isinstance(stale.media, StoredVideo) and isinstance(fresh.media, VideoFile)


async def test_restart_refunds_unfinished_round(session_factory, tmp_path):
    async with session_factory() as session:
        await UserRepository(session).upsert(telegram_id=PLAYER, first_name="P")
        charts = ChartRepository(session)
        machine = await charts.open_machine(CHAT, PLAYER)
        assert machine is not None
        await charts.set_message(machine, 42)
        round_id = await charts.start_round(machine, crash=300)
        await charts.add_bet(round_id, PLAYER, 1000, None)
        await session.commit()
    growth = tmp_path / "growth.mp4"
    growth.write_bytes(b"growth")
    videos = ChartVideos(
        session_factory,
        growth=growth,
        opening=tmp_path / "opening.mp4",
        render_opening=fake_opening,
        executor=lambda: ThreadPoolExecutor(1),
        warm=(),
    )
    service = ChartGameService(session_factory, videos)
    service.screen = screen = FakeScreen()

    await service.start()
    await service.close()

    assert await balance(session_factory, PLAYER) == 1000
    (closed,) = screen.screens
    assert (closed.stage, closed.message_id) == (Stage.ABANDONED, 42)
    assert closed.bets == [BetLine(PLAYER, 1000, None, None, 1000)]
    async with session_factory() as session:
        assert await ChartRepository(session).abandoned_machines() == []


async def test_no_machine_without_growth_video(game, tmp_path):
    service, _, _, _ = game
    (tmp_path / "growth.mp4").unlink()

    with pytest.raises(ChartUnavailable):
        await service.open(CHAT, PLAYER)


async def test_requested_crash_video_is_rendered_and_picture_meanwhile(session_factory, tmp_path):
    videos = make_videos(session_factory, tmp_path, warm=(range(100, 103),))
    assert isinstance(await videos.crash(241), Picture)

    videos.start()
    videos.request(241)
    await videos.idle()
    await videos.close()

    assert isinstance(await videos.crash(241), VideoFile)
    assert sorted(path.name for path in (tmp_path / "crash").iterdir()) == [
        "100.mp4", "101.mp4", "102.mp4", "241.mp4",
    ]


async def test_storage_uploads_ahead_and_crash_never_waits_for_upload(session_factory, tmp_path):
    videos = make_videos(session_factory, tmp_path)
    videos.uploader = FakeUploader()

    videos.start()
    videos.request(241)
    await videos.idle()
    await videos.close()

    assert await videos.crash(241) == StoredVideo(
        video_key(tmp_path / "crash" / "241.mp4"), "video:241.mp4"
    )
    assert isinstance(await videos.growth(), StoredVideo)
    assert await videos.crash(300) == await videos.unlabeled(300)
    assert isinstance(await videos.history([241]), StoredPicture)


async def test_crash_edit_reuses_the_strip_of_the_growth_edit(session_factory, tmp_path):
    videos = make_videos(session_factory, tmp_path)
    videos.uploader = FakeUploader()
    clock = FakeTime()
    service = ChartGameService(
        session_factory, videos, clock=clock.clock, sleep=clock.sleep, rng=FixedRandom(0.5)
    )
    service.screen = screen = FakeScreen()
    async with session_factory() as session:
        await UserRepository(session).upsert(telegram_id=PLAYER, first_name="P")
        await session.commit()
    await service.start()
    started = clock.now
    await service.open(CHAT, PLAYER)
    await clock.until_blocked(service)
    for _ in range(2):
        await clock.advance_to(started + CHART_CONFIG.preparation_seconds, service)
        await clock.advance_to(growth_at(started, 1.92), service)
        started = clock.now
    await clock.advance_to(started + CHART_CONFIG.preparation_seconds, service)
    await service.close()

    # Раунд — две правки: рост и обвал, он же подготовка следующего.
    stages = [shown.stage for shown in screen.screens]
    assert stages == [Stage.PREPARATION, *[Stage.GROWTH, Stage.PREPARATION] * 2, Stage.GROWTH]
    second_growth, second_crash = screen.screens[3:5]
    assert isinstance(second_growth.history, StoredPicture)
    assert second_crash.history == second_growth.history
    assert isinstance(second_crash.media, (StoredVideo, StoredPicture))


async def test_crash_without_video_shows_numbered_picture_uploaded_ahead(session_factory, tmp_path):
    def broken_render(path: Path, crash: int) -> None:
        raise RuntimeError("no ffmpeg")

    videos = make_videos(session_factory, tmp_path)
    videos._render = broken_render
    videos.uploader = FakeUploader()

    videos.start()
    videos.request(611)
    await videos.idle()
    await videos.close()

    numbered = await videos.crash(611)
    assert isinstance(numbered, StoredPicture)
    assert numbered != await videos.crash(612)


async def test_warm_up_rests_after_each_render_but_urgent_does_not(session_factory, tmp_path):
    def slow_render(path: Path, crash: int) -> None:
        time.sleep(0.1)
        fake_render(path, crash)

    videos = make_videos(session_factory, tmp_path)
    videos._render = slow_render
    videos._warm_rest = 4.0
    loop = asyncio.get_running_loop()

    videos.start()
    started = loop.time()
    videos.request(241)
    await videos.idle()
    urgent = loop.time() - started

    videos._put(WARM, 242)
    started = loop.time()
    await videos.idle()
    warm = loop.time() - started
    await videos.close()

    assert urgent < 0.4
    assert warm >= 0.45
