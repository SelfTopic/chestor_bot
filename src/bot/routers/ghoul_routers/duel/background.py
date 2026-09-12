"""Фоновые таймауты дуэли - реализованы как `asyncio`-задачи
(`asyncio.create_task`), а НЕ через `scheduled_notifications`/
`NotificationTicker` - та инфраструктура заточена под "один слот на
(юзер, тип уведомления), без payload, poll раз в 30с, просто уведомить",
а не под "выполнить дефолтное действие с полным контекстом конкретной
дуэли". Гонка "нажатие кнопки против сработавшего таймаута" закрывается
не блокировками в коде, а атомарным `DuelSessionRepository.atomic_update`
(UPDATE ... WHERE stage=expected RETURNING) - выигрывает только один из
двух (см. `services.py`/`fight.py`).

Важно: `DatabaseMiddleware` коммитит и ЗАКРЫВАЕТ сессию сразу после
возврата из хендлера (см. `database_middleware.py`) - поэтому эти задачи
НЕ переиспользуют DI-инжектированные сервисы хендлера (их сессия к
моменту срабатывания таймера уже мертва). Они открывают СОБСТВЕННУЮ
сессию через `session_factory` и строят сервисы заново (`build_services`)
- тот же приём, что уже использует `NotificationTicker._tick`."""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from src.database import session_factory

from ....game_configs import DUEL_CONFIG
from .fight import finalize_outcome, run_and_announce_fight
from .services import build_services

logger = logging.getLogger(__name__)

# Сильная ссылка на фоновые задачи - иначе event loop может собрать их
# сборщиком мусора до завершения (asyncio.create_task не хранит ссылку
# сам, это известная ловушка).
_background_tasks: set = set()


def spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def expire_consent(bot: Bot, duel_id: int) -> None:
    await asyncio.sleep(DUEL_CONFIG.invite_timeout_seconds)
    try:
        async with session_factory() as session:
            services = build_services(session, bot)
            updated = await services.duel_service.atomic_update(
                duel_id, "awaiting_consent", stage="done"
            )
            if not updated:
                return
            await services.battle_record_service.release(
                updated.initiator_telegram_id, updated.target_telegram_id
            )
            await session.commit()

        # Кнопки согласия больше не актуальны - удаляем сообщение вместо
        # редактирования (решено в чате), и отдельно уведомляем о таймауте.
        if updated.consent_message_id:
            try:
                await bot.delete_message(
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
                await bot.send_message(chat_id=chat_id, text=timeout_text)
            except TelegramAPIError:
                pass
    except Exception:
        logger.exception("duel %s: consent expiry failed", duel_id)


async def expire_fora(bot: Bot, duel_id: int) -> None:
    await asyncio.sleep(DUEL_CONFIG.serious_or_handicap_timeout_seconds)
    try:
        async with session_factory() as session:
            services = build_services(session, bot)
            updated = await services.duel_service.atomic_update(
                duel_id, "awaiting_serious_or_handicap", stage="running", compress_hp=True
            )
            if not updated:
                return
            result_session = await run_and_announce_fight(bot, updated, services)
            await session.commit()
    except Exception:
        logger.exception("duel %s: fora expiry failed", duel_id)
        return

    if result_session is not None and result_session.stage == "awaiting_winner_choice":
        spawn(expire_outcome(bot, duel_id))


async def expire_outcome(bot: Bot, duel_id: int) -> None:
    await asyncio.sleep(DUEL_CONFIG.winner_choice_timeout_seconds)
    try:
        async with session_factory() as session:
            services = build_services(session, bot)
            updated = await services.duel_service.atomic_update(
                duel_id, "awaiting_winner_choice", stage="done", winner_choice="outcome_release"
            )
            if not updated:
                return
            await finalize_outcome(bot, updated, "outcome_release", services)
            await session.commit()
    except Exception:
        logger.exception("duel %s: outcome expiry failed", duel_id)


__all__ = ["spawn", "expire_consent", "expire_fora", "expire_outcome"]
