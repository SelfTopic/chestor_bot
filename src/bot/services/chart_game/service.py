import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.exceptions import (
    ChartBetsClosed,
    ChartMachineOpen,
    ChartNoBet,
    ChartNoMachine,
    ChartNotEnoughMoney,
    ChartStaleVideo,
    ChartUnavailable,
)
from src.bot.game_configs import CHART_CONFIG
from src.bot.repositories import (
    BalancesLogRepository,
    ChartRepository,
    ChatRepository,
    GhoulRepository,
    SettledBet,
    UserCooldownRepository,
    UserRepository,
    WalletRepository,
)

from ..user import UserService
from .crash_video import crash_picture
from .growth_video import opening_picture
from .history import HISTORY_LENGTH, history_strip
from .rounds import Bet, Phase, Round, draw_crash
from .screen import BetLine, MachineScreen, Screen, Stage
from .videos import ChartVideos, Media, Picture, StoredVideo, VideoFile

logger = logging.getLogger(__name__)


def _wallet(session: AsyncSession) -> UserService:
    return UserService(
        UserRepository(session),
        GhoulRepository(session),
        UserCooldownRepository(session),
        ChatRepository(session),
        BalancesLogRepository(session),
        WalletRepository(session),
    )


@dataclass
class Machine:
    id: int
    chat_id: int
    opened_at: float
    message_id: int | None = None
    round: Round | None = None
    round_id: int = 0
    # Раунд, который только что обвалился: «забрать» после обвала ответит про него.
    previous: Round | None = None
    history: list[int] = field(default_factory=list)


class ChartGameService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        videos: ChartVideos,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._videos = videos
        self._clock = clock
        self._sleep = sleep
        self._rng = rng or random.SystemRandom()
        # Экран собирают роутеры: им нужен бот, а он появляется позже сервиса.
        self.screen: MachineScreen | None = None
        self._machines: dict[int, Machine] = {}
        self._tasks: dict[int, asyncio.Task[None]] = {}

    async def start(self) -> None:
        await self._restore()
        self._videos.start()

    async def close(self) -> None:
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self._videos.close()

    async def idle(self) -> None:
        while self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)

    def is_open(self, chat_id: int) -> bool:
        return chat_id in self._machines

    async def open(self, chat_id: int, user_id: int) -> None:
        if not self._videos.ready:
            raise ChartUnavailable()
        if chat_id in self._machines:
            raise ChartMachineOpen()
        async with self._session_factory() as session:
            machine_id = await ChartRepository(session).open_machine(chat_id, user_id)
            await session.commit()
        if machine_id is None:
            raise ChartMachineOpen()
        machine = self._machines[chat_id] = Machine(machine_id, chat_id, self._clock())
        self._tasks[chat_id] = asyncio.create_task(self._run(machine))

    async def bet(self, chat_id: int, user_id: int, amount: int, target: int | None) -> Bet:
        machine = self._machine(chat_id)
        if machine.round is None:
            raise ChartBetsClosed()
        game, round_id = machine.round, machine.round_id
        bet = game.place(user_id, amount, target, self._clock())
        try:
            async with self._session_factory() as session:
                if await _wallet(session).debit_if_sufficient(user_id, amount, "chart bet") is None:
                    raise ChartNotEnoughMoney()
                await ChartRepository(session).add_bet(round_id, user_id, amount, target)
                await session.commit()
        except BaseException:
            del game.bets[user_id]
            raise
        return bet

    async def cash_out(self, chat_id: int, user_id: int) -> Bet:
        machine = self._machine(chat_id)
        game, round_id = machine.round, machine.round_id
        now = self._clock()
        if game is None or user_id not in game.bets:
            if machine.previous is not None and user_id in machine.previous.bets:
                machine.previous.cash_out(user_id, now)
            raise ChartNoBet()
        bet = game.cash_out(user_id, now)
        assert bet.cashed_at is not None
        async with self._session_factory() as session:
            await _wallet(session).plus_balance(user_id, bet.payout, "chart win")
            await ChartRepository(session).cash_out(round_id, user_id, bet.cashed_at, bet.payout)
            await session.commit()
        return bet

    def _machine(self, chat_id: int) -> Machine:
        machine = self._machines.get(chat_id)
        if machine is None:
            raise ChartNoMachine()
        return machine

    async def _run(self, machine: Machine) -> None:
        try:
            await self._play(machine)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Автомат графика в чате %s сломался", machine.chat_id)
            await self._refund_and_close(machine.id)
        finally:
            self._machines.pop(machine.chat_id, None)
            self._tasks.pop(machine.chat_id, None)

    async def _play(self, machine: Machine) -> None:
        media: Media = Picture(await asyncio.to_thread(opening_picture))
        crash: int | None = None
        results: list[BetLine] = []
        while True:
            game = await self._new_round(machine)
            await self._show(machine, Stage.PREPARATION, media, results, crash)
            await self._sleep_until(game.started_at + CHART_CONFIG.preparation_seconds)
            growth = await self._videos.growth()
            await self._show(machine, Stage.GROWTH, growth, [BetLine.of(b) for b in game.bets.values()])
            await self._sleep_until(game.crashes_at)
            results = await self._settle(machine, game)
            crash = game.crash
            machine.history = [crash, *machine.history][:HISTORY_LENGTH]
            if self._clock() - machine.opened_at >= CHART_CONFIG.machine_lifetime_seconds:
                picture = Picture(await asyncio.to_thread(crash_picture, crash))
                await self._show(machine, Stage.CLOSED, picture, results, crash)
                await self._close(machine.id)
                return
            media = await self._videos.crash(crash)

    async def _new_round(self, machine: Machine) -> Round:
        game = Round(draw_crash(self._rng), self._clock())
        async with self._session_factory() as session:
            machine.round_id = await ChartRepository(session).start_round(machine.id, game.crash)
            await session.commit()
        machine.previous, machine.round = machine.round, game
        self._videos.request(game.crash)
        return game

    async def _settle(self, machine: Machine, game: Round) -> list[BetLine]:
        waiting = {user_id for user_id, bet in game.bets.items() if bet.cashed_at is None}
        bets = game.settle()
        won = [bet for bet in bets if bet.user_id in waiting and bet.cashed_at is not None]
        async with self._session_factory() as session:
            wallet = _wallet(session)
            for bet in won:
                await wallet.plus_balance(bet.user_id, bet.payout, "chart win")
            settled = [SettledBet(bet.user_id, bet.cashed_at, bet.payout) for bet in won]
            await ChartRepository(session).settle_round(machine.round_id, settled)
            await session.commit()
        return [BetLine.of(bet) for bet in bets]

    async def _show(
        self,
        machine: Machine,
        stage: Stage,
        media: Media,
        bets: list[BetLine],
        crash: int | None = None,
    ) -> None:
        assert self.screen is not None
        strip = await asyncio.to_thread(history_strip, machine.history)
        closes_in = machine.opened_at + CHART_CONFIG.machine_lifetime_seconds - self._clock()

        def screen(media: Media) -> Screen:
            return Screen(
                stage, machine.chat_id, machine.message_id, media, strip, bets, crash, closes_in
            )

        try:
            shown = await self.screen.show(screen(media))
        except ChartStaleVideo:
            assert isinstance(media, StoredVideo)
            await self._videos.forget(media)
            media = await self._videos.crash(crash) if crash is not None else await self._videos.growth()
            shown = await self.screen.show(screen(media))

        if isinstance(media, VideoFile) and shown.file_id is not None:
            await self._videos.remember(media, shown.file_id)
        if machine.message_id is None:
            machine.message_id = shown.message_id
            async with self._session_factory() as session:
                await ChartRepository(session).set_message(machine.id, shown.message_id)
                await session.commit()

    async def _sleep_until(self, moment: float) -> None:
        await self._sleep(max(moment - self._clock(), 0.0))

    async def _close(self, machine_id: int) -> None:
        async with self._session_factory() as session:
            await ChartRepository(session).close_machine(machine_id)
            await session.commit()

    async def _refund_and_close(self, machine_id: int) -> list[BetLine]:
        async with self._session_factory() as session:
            charts = ChartRepository(session)
            refunds = await charts.refunds(machine_id)
            wallet = _wallet(session)
            for refund in refunds:
                await wallet.plus_balance(refund.telegram_id, refund.amount, "chart refund")
            await charts.abandon_rounds(machine_id)
            await charts.close_machine(machine_id)
            await session.commit()
        return [BetLine(r.telegram_id, r.amount, None, None, r.amount) for r in refunds]

    async def _restore(self) -> None:
        async with self._session_factory() as session:
            abandoned = await ChartRepository(session).abandoned_machines()
        for machine in abandoned:
            refunded = await self._refund_and_close(machine.machine_id)
            if machine.message_id is None or self.screen is None:
                continue
            try:
                await self.screen.show(
                    Screen(
                        Stage.ABANDONED,
                        machine.chat_id,
                        machine.message_id,
                        Picture(await asyncio.to_thread(opening_picture)),
                        await asyncio.to_thread(history_strip, []),
                        refunded,
                    )
                )
            except Exception:
                logger.exception("Не закрылось сообщение автомата в чате %s", machine.chat_id)

    def phase(self, chat_id: int) -> Phase | None:
        machine = self._machines.get(chat_id)
        if machine is None or machine.round is None:
            return None
        return machine.round.phase(self._clock())
