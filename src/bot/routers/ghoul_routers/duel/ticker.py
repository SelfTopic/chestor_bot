"""
Таймауты дуэли: задача уровня диспетчера, как NotificationTicker. Создаётся в
Dispatcher.__init__, запускается в on_startup, останавливается в on_shutdown.

У прода таймауты — asyncio-задачи, которые хендлер заводит на каждую дуэль
(background.py). Здесь хендлеры ничего не заводят: тикер раз в interval секунд
читает из БД дуэли, ждущие согласия, выбора "всерьёз/фора" или выбора победителя,
и если дуэль стоит на одной стадии дольше её таймаута (DUEL_CONFIG), делает то же,
что прод по таймауту: отменяет приглашение, начинает бой с форой или отпускает
проигравшего.

Отсчёт идёт с момента, когда тикер впервые увидел дуэль на этой стадии (у
DuelSession нет времени смены стадии), поэтому таймаут может сработать позже на
interval секунд. Зато после перезапуска бота дуэль не зависает навсегда с занятым
ActiveBattle-локом, как у прода, где таймеры жили только в памяти: тикер находит её
заново, и таймаут отсчитывается с запуска.

Гонку "нажатие против таймаута" по-прежнему закрывает atomic_update (UPDATE ...
WHERE stage=ожидаемая): выигрывает кто-то один. Сессию БД тикер открывает сам,
как NotificationTicker: у хендлеров она своя и к этому времени уже закрыта.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from selfrot import Bot
from selfrot.exceptions import TelegramAPIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.containers import Container, session_context
from src.bot.game_configs import DUEL_CONFIG
from src.bot.services.dialog import DialogService
from src.database.models import DuelSession

from ....services.notify import SelfrotBotNotifier
from .fight import finalize_outcome, run_and_announce_fight
from .services import DuelServices

logger = logging.getLogger(__name__)


def stage_timeouts() -> dict[str, float]:
    """Стадии, у которых есть таймаут, и сам таймаут в секундах. Читается на
    каждом тике, а не один раз: так конфиг можно поменять (в тестах — подменить)."""
    return {
        "awaiting_consent": DUEL_CONFIG.invite_timeout_seconds,
        "awaiting_serious_or_handicap": DUEL_CONFIG.serious_or_handicap_timeout_seconds,
        "awaiting_winner_choice": DUEL_CONFIG.winner_choice_timeout_seconds,
    }


class DuelTicker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        bot: Bot,
        container: Container,
        dialog_service: DialogService,
        interval_seconds: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._session_factory = session_factory
        self._bot = bot
        self._container = container
        self._dialog_service = dialog_service
        self._interval = interval_seconds
        self.clock = clock
        # (id дуэли, стадия) -> когда тикер впервые увидел её на этой стадии
        self._seen: dict[tuple[int, str], float] = {}
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is not None:
            logger.warning("DuelTicker is already running")
            return

        logger.info(f"Starting DuelTicker (interval={self._interval}s)")
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is None:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("DuelTicker stopped")

    async def _loop(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:
                logger.error("DuelTicker tick failed", exc_info=True)

            await asyncio.sleep(self._interval)

    async def tick(self) -> None:
        timeouts = stage_timeouts()
        now = self.clock()

        async with self._session_factory() as session:
            rows = await session.execute(
                select(DuelSession.id, DuelSession.stage).where(
                    DuelSession.stage.in_(timeouts)
                )
            )
            waiting = {(duel_id, stage) for duel_id, stage in rows}

        self._seen = {key: self._seen.get(key, now) for key in waiting}

        for key, since in list(self._seen.items()):
            duel_id, stage = key
            if now - since < timeouts[stage]:
                continue

            # Упавший таймаут не повторяется на каждом тике: дуэль увидится заново
            # и получит ещё один полный срок.
            del self._seen[key]
            try:
                await self._expire(duel_id, stage)
            except Exception:
                logger.exception("duel %s: %s expiry failed", duel_id, stage)

    @asynccontextmanager
    async def _services(self) -> AsyncIterator[DuelServices]:
        """Свежая сессия на одно действие, закоммиченная, если оно не упало."""
        async with self._session_factory() as session:
            token = session_context.set(session)
            try:
                yield DuelServices.from_container(
                    self._container,
                    self._dialog_service,
                    SelfrotBotNotifier(self._bot),
                )
                await session.commit()
            finally:
                session_context.reset(token)

    async def _expire(self, duel_id: int, stage: str) -> None:
        if stage == "awaiting_consent":
            await self._expire_consent(duel_id)
        elif stage == "awaiting_serious_or_handicap":
            await self._expire_fora(duel_id)
        else:
            await self._expire_outcome(duel_id)

    async def _expire_consent(self, duel_id: int) -> None:
        async with self._services() as services:
            updated = await services.duel_service.atomic_update(
                duel_id, "awaiting_consent", stage="done"
            )
            if not updated:
                return
            await services.battle_record_service.release(
                updated.initiator_telegram_id, updated.target_telegram_id
            )

        # Кнопки согласия больше не актуальны: сообщение удаляется, а о таймауте
        # сообщается отдельно.
        if updated.consent_message_id:
            try:
                await self._bot.delete_message(
                    chat_id=updated.chat_id, message_id=updated.consent_message_id
                )
            except TelegramAPIError:
                pass

        timeout_text = "⌛ Время на согласие вышло - дуэль отменена."
        target_chat_ids = {updated.initiator_telegram_id, updated.target_telegram_id}
        if not updated.is_private_origin:
            target_chat_ids.add(updated.chat_id)
        for chat_id in target_chat_ids:
            try:
                await self._bot.send_message(chat_id=chat_id, text=timeout_text)
            except TelegramAPIError:
                pass

    async def _expire_fora(self, duel_id: int) -> None:
        """Сильная сторона не выбрала: бой с форой (BATTLE_ENGINE.md 1.5)."""
        async with self._services() as services:
            updated = await services.duel_service.atomic_update(
                duel_id,
                "awaiting_serious_or_handicap",
                stage="running",
                compress_hp=True,
            )
            if updated:
                await run_and_announce_fight(self._bot, updated, services)

    async def _expire_outcome(self, duel_id: int) -> None:
        """Победитель не выбрал: проигравшего отпускают."""
        async with self._services() as services:
            updated = await services.duel_service.atomic_update(
                duel_id,
                "awaiting_winner_choice",
                stage="done",
                winner_choice="outcome_release",
            )
            if updated:
                await finalize_outcome(self._bot, updated, "outcome_release", services)
