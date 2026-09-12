"""Общая логика "разыграть бой и объявить результат" / "применить выбор
победителя" - используется и живыми колбэками (`duel_process_router.py`),
и фоновыми таймаутами (`background.py`), поэтому ничего не знает про то,
кто её вызвал (только `Services`, собранные тем или иным способом, см.
`services.py`) и НЕ спавнит следующий таймаут само - это ответственность
вызывающего кода (см. `run_and_announce_fight`'s докстринг)."""

import logging
import random
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from src.database.models import DuelSession

from ....game_configs import DUEL_CONFIG
from ....services import BattleService
from .keyboards import outcome_keyboard
from .services import Services

logger = logging.getLogger(__name__)


async def run_and_announce_fight(
    bot: Bot, duel_session: DuelSession, services: Services
) -> Optional[DuelSession]:
    """Возвращает итоговое состояние `DuelSession` после боя - `None`,
    если один из участников исчез между шагами (страховка). Если
    `.stage == "awaiting_winner_choice"` в возврате - вызывающий код
    обязан сам заспавнить таймаут на выбор победителя (см.
    `background.expire_outcome`) - эта функция намеренно этого не делает,
    чтобы не тянуть сюда зависимость от фоновых задач (см. докстринг
    модуля)."""

    initiator_ghoul = await services.ghoul_service.get(duel_session.initiator_telegram_id)
    target_ghoul = await services.ghoul_service.get(duel_session.target_telegram_id)
    initiator_user = await services.user_service.get(find_by=duel_session.initiator_telegram_id)
    target_user = await services.user_service.get(find_by=duel_session.target_telegram_id)

    if not initiator_ghoul or not target_ghoul or not initiator_user or not target_user:
        logger.error("duel %s: participant vanished mid-flow", duel_session.id)
        await services.battle_record_service.release(
            duel_session.initiator_telegram_id, duel_session.target_telegram_id
        )
        await services.duel_service.atomic_update(duel_session.id, "running", stage="done")
        return None

    fighter_a = services.battle_service.ghoul_to_fighter(
        initiator_ghoul, initiator_user.full_name, services.ghoul_service
    )
    fighter_b = services.battle_service.ghoul_to_fighter(
        target_ghoul, target_user.full_name, services.ghoul_service
    )

    compress_hp = duel_session.compress_hp if duel_session.compress_hp is not None else True
    result = services.battle_service.run_duel(fighter_a, fighter_b, compress_hp=compress_hp)

    new_health_a = BattleService.resolve_post_battle_health(
        initiator_ghoul.health, result.stats_a.health, result.final_hp_a
    )
    new_health_b = BattleService.resolve_post_battle_health(
        target_ghoul.health, result.stats_b.health, result.final_hp_b
    )
    await services.ghoul_service.set_fields(duel_session.initiator_telegram_id, health=new_health_a)
    await services.ghoul_service.set_fields(duel_session.target_telegram_id, health=new_health_b)

    rank_a = services.ghoul_service.get_danger_rank(
        services.battle_service.power_of(fighter_a.snapshot)
    )
    rank_b = services.ghoul_service.get_danger_rank(
        services.battle_service.power_of(fighter_b.snapshot)
    )

    winner_telegram_id: Optional[int] = None
    loser_telegram_id: Optional[int] = None
    reward_level_progress: Optional[float] = None

    if result.winner is not None:
        is_initiator_winner = result.winner == "a"
        winner_telegram_id = (
            duel_session.initiator_telegram_id
            if is_initiator_winner
            else duel_session.target_telegram_id
        )
        loser_telegram_id = (
            duel_session.target_telegram_id
            if is_initiator_winner
            else duel_session.initiator_telegram_id
        )
        winner_ghoul = initiator_ghoul if is_initiator_winner else target_ghoul
        loser_ghoul = target_ghoul if is_initiator_winner else initiator_ghoul
        winner_power = services.ghoul_service.calculate_power(winner_ghoul)
        loser_power = services.ghoul_service.calculate_power(loser_ghoul)
        # Формула левел-апа (BATTLE_DESIGN.md) - 1% * (сила соперника / своя сила).
        reward_level_progress = 1.0 * loser_power / winner_power if winner_power > 0 else 0.0
        await services.level_up_service.add_progress(winner_telegram_id, reward_level_progress)

    rich_message = services.battle_text_generator.build_rich_message(
        result, fighter_a, fighter_b, rank_a, rank_b
    )
    keyboard = outcome_keyboard(duel_session.id, winner_telegram_id) if winner_telegram_id else None

    sent = None
    try:
        sent = await bot.send_rich_message(
            chat_id=duel_session.chat_id, rich_message=rich_message, reply_markup=keyboard
        )
    except TelegramAPIError:
        fallback_text = services.battle_text_generator.build_plain_text(
            result, fighter_a, fighter_b, rank_a, rank_b
        )
        try:
            sent = await bot.send_message(
                chat_id=duel_session.chat_id, text=fallback_text, reply_markup=keyboard
            )
        except TelegramAPIError:
            logger.warning("duel %s: failed to announce fight result", duel_session.id)

    if winner_telegram_id is None or loser_telegram_id is None:
        # Настоящая ничья (тай-брейк не спас, см. BATTLE_ENGINE.md 2.6) -
        # выбирать нечего, пишем историю сразу.
        await services.battle_record_service.record_duel(
            duel_session.initiator_telegram_id,
            duel_session.target_telegram_id,
            winner=None,
            ended_naturally=result.ended_naturally,
            is_forced=False,
        )
        await services.battle_record_service.release(
            duel_session.initiator_telegram_id, duel_session.target_telegram_id
        )
        return await services.duel_service.atomic_update(duel_session.id, "running", stage="done")

    return await services.duel_service.atomic_update(
        duel_session.id,
        "running",
        stage="awaiting_winner_choice",
        winner_telegram_id=winner_telegram_id,
        loser_telegram_id=loser_telegram_id,
        outcome_message_id=sent.message_id if sent else None,
        reward_level_progress=reward_level_progress,
        ended_naturally=result.ended_naturally,
    )


async def finalize_outcome(
    bot: Bot, duel_session: DuelSession, action: str, services: Services
) -> None:
    """Применяет исход "ограбить/отпустить/съесть" - вызывать ТОЛЬКО
    после того, как `atomic_update` реально перевёл сессию в стадию
    "done" с этим `winner_choice` (то есть эта сторона гонки выиграла) -
    ни живой колбэк, ни таймаут-заглушка сюда не попадают, если проиграли
    гонку друг другу."""

    assert duel_session.winner_telegram_id is not None
    assert duel_session.loser_telegram_id is not None
    winner_id = duel_session.winner_telegram_id
    loser_id = duel_session.loser_telegram_id

    reward_rc: Optional[int] = None
    reward_balance: Optional[int] = None

    if action == "outcome_rob":
        loser_user = await services.user_service.get(find_by=loser_id)
        if loser_user and loser_user.balance > 0:
            percent = random.uniform(DUEL_CONFIG.rob_percent_min, DUEL_CONFIG.rob_percent_max)
            amount = round(loser_user.balance * percent / 100.0)
            if amount > 0:
                await services.user_service.minus_balance(
                    loser_id, amount, log=f"duel robbery by {winner_id}"
                )
                await services.user_service.plus_balance(
                    winner_id, amount, log=f"duel robbery from {loser_id}"
                )
                reward_balance = amount
    elif action == "outcome_eat":
        loser_ghoul = await services.ghoul_service.get(loser_id)
        if loser_ghoul:
            power = services.ghoul_service.calculate_power(loser_ghoul)
            rc = round(
                power
                * random.uniform(DUEL_CONFIG.eat_rc_multiplier_min, DUEL_CONFIG.eat_rc_multiplier_max)
            )
            if rc > 0:
                await services.ghoul_service.increment_fields(winner_id, rc_money=rc)
                reward_rc = rc
        await services.ghoul_service.apply_death(loser_id, cause="eaten", killer_telegram_id=winner_id)

    winner_label = "a" if winner_id == duel_session.initiator_telegram_id else "b"
    await services.battle_record_service.record_duel(
        duel_session.initiator_telegram_id,
        duel_session.target_telegram_id,
        winner=winner_label,
        ended_naturally=duel_session.ended_naturally
        if duel_session.ended_naturally is not None
        else True,
        is_forced=False,
        winner_choice=action.removeprefix("outcome_"),
        reward_level_progress=duel_session.reward_level_progress,
        reward_rc=reward_rc,
        reward_balance=reward_balance,
    )
    await services.battle_record_service.release(
        duel_session.initiator_telegram_id, duel_session.target_telegram_id
    )

    choice_label = {
        "outcome_rob": "ограбить 💰",
        "outcome_release": "отпустить 🕊️",
        "outcome_eat": "съесть 🍖",
    }[action]

    if duel_session.outcome_message_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=duel_session.chat_id,
                message_id=duel_session.outcome_message_id,
                reply_markup=None,
            )
        except TelegramAPIError:
            pass
    try:
        await bot.send_message(
            chat_id=duel_session.chat_id, text=f"Победитель выбрал: {choice_label}."
        )
    except TelegramAPIError:
        pass


__all__ = ["run_and_announce_fight", "finalize_outcome"]
