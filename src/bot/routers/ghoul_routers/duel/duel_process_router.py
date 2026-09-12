"""Шаги 2/3/5 - обработка нажатий по уже отправленной дуэли: согласие
обеих сторон -> (при перевесе >= `DUEL_CONFIG.power_ratio_threshold`)
секретный выбор "всерьёз/фора" в ЛС сильной стороны -> сам бой
(`fight.run_and_announce_fight`) -> выбор победителя "ограбить/отпустить/
съесть" (`fight.finalize_outcome`). Таймауты каждого шага - `background.py`."""

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message
from dependency_injector.wiring import Provide, inject

from ....containers import Container
from ....game_configs import DUEL_CONFIG
from ....services import (
    BattleRecordService,
    BattleService,
    BattleTextGenerator,
    DuelService,
    GhoulService,
    LevelUpService,
    UserService,
)
from .background import expire_fora, expire_outcome, spawn
from .callback_data import parse_duel_callback_payload
from .fight import finalize_outcome, run_and_announce_fight
from .keyboards import consent_keyboard, fora_keyboard
from .services import Services

router = Router(name=__name__)
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("duel:"))
@inject
async def duel_callback_handler(
    callback_query: CallbackQuery,
    bot: Bot,
    user_service: UserService = Provide[Container.user_service],
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    battle_service: BattleService = Provide[Container.battle_service],
    battle_text_generator: BattleTextGenerator = Provide[Container.battle_text_generator],
    level_up_service: LevelUpService = Provide[Container.level_up_service],
    battle_record_service: BattleRecordService = Provide[Container.battle_record_service],
    duel_service: DuelService = Provide[Container.duel_service],
) -> None:
    if not callback_query.data or not callback_query.from_user:
        await callback_query.answer()
        return None

    parsed = parse_duel_callback_payload(callback_query.data)
    if not parsed:
        await callback_query.answer()
        return None
    duel_id, action, expected_telegram_id = parsed

    if callback_query.from_user.id != expected_telegram_id:
        await callback_query.answer("Это не твоя кнопка.", show_alert=True)
        return None

    services = Services(
        user_service=user_service,
        ghoul_service=ghoul_service,
        battle_service=battle_service,
        battle_text_generator=battle_text_generator,
        level_up_service=level_up_service,
        battle_record_service=battle_record_service,
        duel_service=duel_service,
    )

    if action in ("consent_initiator", "consent_target"):
        await _handle_consent(callback_query, bot, duel_id, action, services)
    elif action in ("fora_serious", "fora_handicap"):
        await _handle_fora(callback_query, bot, duel_id, action, services)
    else:
        await _handle_outcome(callback_query, bot, duel_id, action, services)

    return None


async def _handle_consent(
    callback_query: CallbackQuery, bot: Bot, duel_id: int, action: str, services: Services
) -> None:
    field = "initiator_consented" if action == "consent_initiator" else "target_consented"
    updated = await services.duel_service.atomic_update(duel_id, "awaiting_consent", **{field: True})
    if not updated:
        await callback_query.answer("Приглашение уже неактуально.", show_alert=True)
        return

    if not (updated.initiator_consented and updated.target_consented):
        await callback_query.answer("Принято, ждём второго участника.")
        if updated.consent_message_id:
            try:
                await bot.edit_message_text(
                    chat_id=updated.chat_id,
                    message_id=updated.consent_message_id,
                    text="✅ Один из участников подтвердил, ждём второго.",
                    reply_markup=consent_keyboard(
                        duel_id, updated.initiator_telegram_id, updated.target_telegram_id
                    ),
                )
            except TelegramAPIError:
                pass
        return

    await callback_query.answer("Оба подтвердили!")

    initiator_ghoul = await services.ghoul_service.get(updated.initiator_telegram_id)
    target_ghoul = await services.ghoul_service.get(updated.target_telegram_id)
    if not initiator_ghoul or not target_ghoul:
        await services.battle_record_service.release(
            updated.initiator_telegram_id, updated.target_telegram_id
        )
        await services.duel_service.atomic_update(duel_id, "awaiting_consent", stage="done")
        return

    fighter_a = services.battle_service.ghoul_to_fighter(initiator_ghoul, "a", services.ghoul_service)
    fighter_b = services.battle_service.ghoul_to_fighter(target_ghoul, "b", services.ghoul_service)
    power_a = services.battle_service.power_of(fighter_a.snapshot)
    power_b = services.battle_service.power_of(fighter_b.snapshot)
    weaker_power = min(power_a, power_b)
    stronger_power = max(power_a, power_b)
    power_ratio = stronger_power / weaker_power if weaker_power > 0 else float("inf")

    if power_ratio < DUEL_CONFIG.power_ratio_threshold:
        session = await services.duel_service.atomic_update(
            duel_id, "awaiting_consent", stage="running", compress_hp=True
        )
        if not session:
            return
        result_session = await run_and_announce_fight(bot, session, services)
        if result_session is not None and result_session.stage == "awaiting_winner_choice":
            spawn(expire_outcome(bot, duel_id))
        return

    favored_id = updated.initiator_telegram_id if power_a >= power_b else updated.target_telegram_id
    session = await services.duel_service.atomic_update(
        duel_id,
        "awaiting_consent",
        stage="awaiting_serious_or_handicap",
        favored_telegram_id=favored_id,
    )
    if not session:
        return

    if updated.consent_message_id:
        try:
            await bot.edit_message_text(
                chat_id=updated.chat_id,
                message_id=updated.consent_message_id,
                text="⚔️ Оба согласились! Ждём решения сильнейшей стороны.",
            )
        except TelegramAPIError:
            pass

    try:
        await bot.send_message(
            chat_id=favored_id,
            text="Ты значительно сильнее соперника. Драться всерьёз или дать фору?",
            reply_markup=fora_keyboard(duel_id, favored_id),
        )
    except TelegramAPIError:
        logger.warning("duel %s: failed to DM fora choice", duel_id)

    spawn(expire_fora(bot, duel_id))


async def _handle_fora(
    callback_query: CallbackQuery, bot: Bot, duel_id: int, action: str, services: Services
) -> None:
    compress_hp = action == "fora_handicap"
    session = await services.duel_service.atomic_update(
        duel_id, "awaiting_serious_or_handicap", stage="running", compress_hp=compress_hp
    )
    if not session:
        await callback_query.answer("Уже неактуально.", show_alert=True)
        return

    await callback_query.answer("Принято!")
    if isinstance(callback_query.message, Message):
        try:
            await callback_query.message.edit_text("Решение принято, бой начинается.")
        except TelegramAPIError:
            pass

    result_session = await run_and_announce_fight(bot, session, services)
    if result_session is not None and result_session.stage == "awaiting_winner_choice":
        spawn(expire_outcome(bot, duel_id))


async def _handle_outcome(
    callback_query: CallbackQuery, bot: Bot, duel_id: int, action: str, services: Services
) -> None:
    session = await services.duel_service.atomic_update(
        duel_id, "awaiting_winner_choice", stage="done", winner_choice=action
    )
    if not session:
        await callback_query.answer("Уже неактуально.", show_alert=True)
        return

    await callback_query.answer("Принято!")
    await finalize_outcome(bot, session, action, services)


__all__ = ["router"]
