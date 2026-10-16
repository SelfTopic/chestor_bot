import logging

from selfrot import Bot
from selfrot.exceptions import TelegramAPIError

from src.bot.dialogs import Dialogs
from src.bot.game_configs import DUEL_CONFIG
from src.bot.session_services import SessionServices

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
# Каждая дуэль — своя транзакция: сбой одной не откатывает уже истёкшие.
async def expire_overdue_duels(services: SessionServices, bot: Bot) -> None:
    duels = DuelServices.from_services(services)
    for duel_id, stage in await duels.duel_service.overdue(stage_timeouts()):
        try:
            if stage == "awaiting_consent":
                await _expire_consent(services, duels, bot, duel_id)
            elif stage == "awaiting_serious_or_handicap":
                await _expire_fora(duels, bot, duel_id)
            else:
                await _expire_outcome(duels, bot, duel_id)
            await services.session.commit()
        except Exception:
            logger.exception("duel %s: %s expiry failed", duel_id, stage)
            await services.session.rollback()
            # Иначе упавший таймаут повторялся бы каждый тик: следующая попытка — через
            # полный срок стадии.
            await duels.duel_service.restart_countdown(duel_id, stage)
            await services.session.commit()


async def _expire_consent(
    services: SessionServices, duels: DuelServices, bot: Bot, duel_id: int
) -> None:
    updated = await duels.duel_service.atomic_update(duel_id, "awaiting_consent", stage="done")
    if not updated:
        return
    await duels.battle_record_service.release(
        updated.initiator_telegram_id, updated.target_telegram_id
    )
    # Объявление — после коммита: откат не должен оставить в чате «дуэль отменена».
    await services.session.commit()

    if updated.consent_message_id:
        try:
            await bot.delete_message(chat_id=updated.chat_id, message_id=updated.consent_message_id)
        except TelegramAPIError:
            pass

    timeout_text = duels.dialogs.text(Dialogs.duel.consent.timeout())
    target_chat_ids = {updated.initiator_telegram_id, updated.target_telegram_id}
    if not updated.is_private_origin:
        target_chat_ids.add(updated.chat_id)
    for chat_id in target_chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=timeout_text)
        except TelegramAPIError:
            pass


async def _expire_fora(duels: DuelServices, bot: Bot, duel_id: int) -> None:
    updated = await duels.duel_service.atomic_update(
        duel_id, "awaiting_serious_or_handicap", stage="running", compress_hp=True
    )
    if updated:
        await run_and_announce_fight(bot, updated, duels)


async def _expire_outcome(duels: DuelServices, bot: Bot, duel_id: int) -> None:
    updated = await duels.duel_service.atomic_update(
        duel_id, "awaiting_winner_choice", stage="done", winner_choice="outcome_release"
    )
    if updated:
        await finalize_outcome(bot, updated, "outcome_release", duels)
