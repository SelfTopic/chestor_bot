import asyncio
import dataclasses
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.exceptions import (
    RouletteBetOutOfRange,
    RouletteBusy,
    RouletteNoChoice,
    RouletteNoMachine,
    RouletteNotEnoughMoney,
    RouletteNotYours,
    RouletteStaleMedia,
)
from src.bot.game_configs import LOTTERY_CONFIG
from src.bot.repositories import LotteryRepository, RouletteRepository
from src.bot.types.dep import DepColor

from ..arcade.media import Media, Picture, StoredPicture, StoredVideo, VideoFile
from ..arcade.wallet import wallet
from .positions import POSITIONS, VARIANTS, Clip, positions_of
from .screen import RouletteScreen, Screen, Stage
from .spin_video import LANDED_SECONDS
from .spins import Choice, Outcome, draw_color, winnings
from .videos import RouletteVideos

logger = logging.getLogger(__name__)


@dataclass
class Machine:
    id: int
    chat_id: int
    user_id: int
    position: int
    choice: Choice
    closes_at: float
    message_id: int | None = None
    outcome: Outcome | None = None
    spinning: bool = False


class RouletteService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        videos: RouletteVideos,
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
        self.screen: RouletteScreen | None = None
        self._machines: dict[int, Machine] = {}
        self._owners: dict[tuple[int, int], int] = {}
        self._watchers: dict[int, asyncio.Task[None]] = {}
        self._landings: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        await self._restore()
        self._videos.start()

    async def close(self) -> None:
        tasks = [*self._watchers.values(), *self._landings]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self._videos.close()

    async def idle(self) -> None:
        while self._landings:
            await asyncio.gather(*self._landings, return_exceptions=True)

    async def open(
        self, chat_id: int, user_id: int, color: DepColor | None = None, amount: int | None = None
    ) -> None:
        self._check(amount)
        previous = self._owned(chat_id, user_id)
        if previous is not None and previous.spinning:
            raise RouletteBusy()
        # Новый автомат продолжает ленту и ставку прежнего: он просто переезжает вниз чата.
        if previous is not None:
            position, choice = previous.position, previous.choice
            await self._close(previous)
        else:
            position, choice = self._rng.randrange(len(POSITIONS)), Choice()
        async with self._session_factory() as session:
            machine_id = await RouletteRepository(session).open_machine(chat_id, user_id, position)
            await session.commit()
        if machine_id is None:
            raise RouletteBusy()
        machine = Machine(
            machine_id,
            chat_id,
            user_id,
            position,
            choice.merged(color, amount),
            self._clock() + LOTTERY_CONFIG.idle_seconds,
        )
        self._machines[machine.id] = machine
        self._owners[chat_id, user_id] = machine.id
        try:
            await self._show_ready(machine)
        except BaseException:
            await self._forget(machine)
            raise
        self._watchers[machine.id] = asyncio.create_task(self._watch(machine))

    async def choose(
        self,
        machine_id: int,
        user_id: int,
        color: DepColor | None = None,
        amount: int | None = None,
    ) -> Choice:
        self._check(amount)
        machine = self._own(machine_id, user_id)
        machine.choice = machine.choice.merged(color, amount)
        # Пока лента едет, сообщение не трогаем: новая ставка появится вместе с итогом.
        if not machine.spinning:
            machine.closes_at = self._clock() + LOTTERY_CONFIG.idle_seconds
            await self._show_ready(machine)
        return machine.choice

    async def spin(self, machine_id: int, user_id: int) -> None:
        machine = self._own(machine_id, user_id)
        if machine.spinning:
            raise RouletteBusy()
        choice = machine.choice
        if choice.color is None or choice.amount is None:
            raise RouletteNoChoice()
        machine.spinning = True
        flight = LANDED_SECONDS + LOTTERY_CONFIG.playback_delay_seconds
        machine.closes_at = self._clock() + flight + LOTTERY_CONFIG.idle_seconds
        try:
            winning = draw_color(self._rng)
            outcome = await self._settle(user_id, choice.color, choice.amount, winning)
        except BaseException:
            machine.spinning = False
            raise
        clip = self._clip(machine.position, winning)
        video = await self._videos.spin(clip)
        if video is None:
            await self._land(machine, clip.end, outcome)
            return
        try:
            await self._show(machine, Stage.SPINNING, video, outcome, clip)
        except Exception:
            logger.exception("Прокрут рулетки в чате %s не показался", machine.chat_id)
            await self._land(machine, clip.end, outcome)
            return
        task = asyncio.create_task(self._land_later(machine, clip.end, outcome, flight))
        self._landings.add(task)
        task.add_done_callback(self._landings.discard)

    def _check(self, amount: int | None) -> None:
        if amount is not None and not LOTTERY_CONFIG.min_bet <= amount <= LOTTERY_CONFIG.max_bet:
            raise RouletteBetOutOfRange(LOTTERY_CONFIG.min_bet, LOTTERY_CONFIG.max_bet)

    def _owned(self, chat_id: int, user_id: int) -> Machine | None:
        machine_id = self._owners.get((chat_id, user_id))
        return None if machine_id is None else self._machines.get(machine_id)

    def _own(self, machine_id: int, user_id: int) -> Machine:
        machine = self._machines.get(machine_id)
        if machine is None:
            raise RouletteNoMachine()
        if machine.user_id != user_id:
            raise RouletteNotYours()
        return machine

    def _clip(self, start: int, winning: DepColor) -> Clip:
        candidates = [
            Clip(start, end, variant)
            for end in positions_of(winning)
            for variant in range(VARIANTS)
        ]
        ready = [clip for clip in candidates if self._videos.ready(clip)]
        return self._rng.choice(ready or candidates)

    # Выплата прежней лотереи: при выигрыше игрок получает ставку × коэффициент сверх ставки.
    async def _settle(self, user_id: int, color: DepColor, bet: int, winning: DepColor) -> Outcome:
        async with self._session_factory() as session:
            purse = wallet(session)
            balance = await purse.debit_if_sufficient(user_id, bet, "lottery bet")
            if balance is None:
                raise RouletteNotEnoughMoney()
            won = color is winning
            earned = winnings(winning, bet) if won else -bet
            if won:
                balance = await purse.plus_balance(user_id, bet + earned, "lottery win")
            await LotteryRepository(session).insert(
                telegram_id=user_id,
                bet_amount=bet,
                chosen_color=color.value,
                winning_color=winning.value,
                is_won=won,
                earned=earned,
            )
            await session.commit()
        return Outcome(color, winning, bet, earned, balance)

    async def _land_later(self, machine: Machine, end: int, outcome: Outcome, flight: float) -> None:
        await self._sleep(flight)
        await self._land(machine, end, outcome)

    async def _land(self, machine: Machine, end: int, outcome: Outcome) -> None:
        machine.position, machine.outcome, machine.spinning = end, outcome, False
        machine.closes_at = self._clock() + LOTTERY_CONFIG.idle_seconds
        try:
            async with self._session_factory() as session:
                await RouletteRepository(session).set_position(machine.id, end)
                await session.commit()
            await self._show_ready(machine)
        except Exception:
            logger.exception("Итог рулетки в чате %s не показался", machine.chat_id)

    async def _watch(self, machine: Machine) -> None:
        while (left := machine.closes_at - self._clock()) > 0 or machine.spinning:
            await self._sleep(max(left, 0.0))
        self._watchers.pop(machine.id, None)
        try:
            await self._close(machine)
        except Exception:
            logger.exception("Автомат рулетки в чате %s не закрылся", machine.chat_id)

    async def _close(self, machine: Machine) -> None:
        watcher = self._watchers.pop(machine.id, None)
        if watcher is not None:
            watcher.cancel()
        await self._forget(machine)
        assert self.screen is not None
        picture = Picture(await self.screen.closed_picture(machine.chat_id, machine.position))
        await self._show(machine, Stage.CLOSED, picture, machine.outcome)

    async def _forget(self, machine: Machine) -> None:
        self._machines.pop(machine.id, None)
        if self._owners.get((machine.chat_id, machine.user_id)) == machine.id:
            del self._owners[machine.chat_id, machine.user_id]
        async with self._session_factory() as session:
            await RouletteRepository(session).close_machine(machine.id)
            await session.commit()

    async def _show_ready(self, machine: Machine) -> None:
        media = await self._videos.rest(machine.position)
        await self._show(machine, Stage.READY, media, machine.outcome)

    async def _show(
        self,
        machine: Machine,
        stage: Stage,
        media: Media,
        outcome: Outcome | None,
        clip: Clip | None = None,
    ) -> None:
        assert self.screen is not None
        async with self._session_factory() as session:
            balance = await wallet(session).balance(machine.user_id)
        screen = Screen(
            stage,
            machine.id,
            machine.chat_id,
            machine.user_id,
            machine.message_id,
            media,
            machine.choice,
            balance,
            outcome,
        )
        try:
            shown = await self.screen.show(screen)
        except RouletteStaleMedia:
            if isinstance(media, StoredVideo) and clip is not None:
                media = await self._videos.fresh_spin(media, clip)
            elif isinstance(media, StoredPicture):
                media = await self._videos.fresh_rest(machine.position)
            else:
                raise
            shown = await self.screen.show(dataclasses.replace(screen, media=media))
        if isinstance(media, VideoFile) and shown.file_id is not None:
            await self._videos.remember(media, shown.file_id)
        if machine.message_id is None:
            machine.message_id = shown.message_id
            async with self._session_factory() as session:
                await RouletteRepository(session).set_message(machine.id, shown.message_id)
                await session.commit()

    async def _restore(self) -> None:
        async with self._session_factory() as session:
            abandoned = await RouletteRepository(session).open_machines()
            for machine in abandoned:
                await RouletteRepository(session).close_machine(machine.machine_id)
            await session.commit()
        if self.screen is None:
            return
        for row in abandoned:
            if row.message_id is None:
                continue
            machine = Machine(
                row.machine_id, row.chat_id, row.telegram_id, row.position, Choice(), 0.0, row.message_id
            )
            try:
                picture = await self.screen.closed_picture(row.chat_id, row.position)
                await self._show(machine, Stage.CLOSED, Picture(picture), None)
            except Exception:
                logger.exception("Не закрылось сообщение рулетки в чате %s", row.chat_id)
