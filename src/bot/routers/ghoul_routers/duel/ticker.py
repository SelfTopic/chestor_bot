import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from selfrot import Bot
from selfrot.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.dialogs import Dialogs
from src.bot.game_configs import DUEL_CONFIG
from src.bot.services import MobService
from src.bot.services.dialog import DialogService
from src.bot.session_services import SessionServices, session_context

from ....services.notify import SelfrotBotNotifier
from ....services.ticker import Ticker
from .fight import finalize_outcome, run_and_announce_fight
from .services import DuelServices

logger = logging.getLogger(__name__)


def stage_timeouts() -> dict[str, float]:
    return {
        "awaiting_consent": DUEL_CONFIG.invite_timeout_seconds,
        "awaiting_serious_or_handicap": DUEL_CONFIG.serious_or_handicap_timeout_seconds,
        "awaiting_winner_choice": DUEL_CONFIG.winner_choice_timeout_seconds,
    }


# Гонку «нажатие против таймаута» закрывает atomic_update: стадию уводит тот, кто первый.
class DuelTicker(Ticker):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        bot: Bot,
        dialog_service: DialogService,
        mob_service: MobService,
        interval_seconds: float = 1.0,
    ) -> None:
        super().__init__(interval_seconds)
        self._session_factory = session_factory
        self._bot = bot
        self._dialog_service = dialog_service
        self._mob_service = mob_service

    async def tick(self) -> None:
        async with self._services() as services:
            overdue = await services.duel_service.overdue(stage_timeouts())

        for duel_id, stage in overdue:
            try:
                await self._expire(duel_id, stage)
            except Exception:
                logger.exception("duel %s: %s expiry failed", duel_id, stage)
                # Иначе упавший таймаут повторялся бы каждый тик: следующая попытка — через
                # полный срок стадии.
                async with self._services() as services:
                    await services.duel_service.restart_countdown(duel_id, stage)

    @asynccontextmanager
    async def _services(self) -> AsyncIterator[DuelServices]:
        async with self._session_factory() as session:
            token = session_context.set(session)
            try:
                yield DuelServices.from_services(
                    SessionServices(
                        self._dialog_service, SelfrotBotNotifier(self._bot), self._mob_service
                    )
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

        if updated.consent_message_id:
            try:
                await self._bot.delete_message(
                    chat_id=updated.chat_id, message_id=updated.consent_message_id
                )
            except TelegramAPIError:
                pass

        timeout_text = self._dialog_service.text(Dialogs.duel.consent.timeout())
        target_chat_ids = {updated.initiator_telegram_id, updated.target_telegram_id}
        if not updated.is_private_origin:
            target_chat_ids.add(updated.chat_id)
        for chat_id in target_chat_ids:
            try:
                await self._bot.send_message(chat_id=chat_id, text=timeout_text)
            except TelegramAPIError:
                pass

    async def _expire_fora(self, duel_id: int) -> None:
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
        async with self._services() as services:
            updated = await services.duel_service.atomic_update(
                duel_id,
                "awaiting_winner_choice",
                stage="done",
                winner_choice="outcome_release",
            )
            if updated:
                await finalize_outcome(self._bot, updated, "outcome_release", services)
