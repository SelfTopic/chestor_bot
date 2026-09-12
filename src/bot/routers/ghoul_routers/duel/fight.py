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
from ....utils import utcnow_naive
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

    initiator_ghoul = await services.ghoul_service.get(
        duel_session.initiator_telegram_id
    )
    target_ghoul = await services.ghoul_service.get(duel_session.target_telegram_id)
    initiator_user = await services.user_service.get(
        find_by=duel_session.initiator_telegram_id
    )
    target_user = await services.user_service.get(
        find_by=duel_session.target_telegram_id
    )

    if not initiator_ghoul or not target_ghoul or not initiator_user or not target_user:
        logger.error("duel %s: participant vanished mid-flow", duel_session.id)
        await services.battle_record_service.release(
            duel_session.initiator_telegram_id, duel_session.target_telegram_id
        )
        await services.duel_service.atomic_update(
            duel_session.id, "running", stage="done"
        )
        return None

    fighter_a = services.battle_service.ghoul_to_fighter(
        initiator_ghoul, initiator_user.full_name, services.ghoul_service
    )
    fighter_b = services.battle_service.ghoul_to_fighter(
        target_ghoul, target_user.full_name, services.ghoul_service
    )

    compress_hp = (
        duel_session.compress_hp if duel_session.compress_hp is not None else True
    )
    result = services.battle_service.run_duel(
        fighter_a, fighter_b, compress_hp=compress_hp
    )

    new_health_a = BattleService.resolve_post_battle_health(
        initiator_ghoul.health, result.stats_a.health, result.final_hp_a
    )
    new_health_b = BattleService.resolve_post_battle_health(
        target_ghoul.health, result.stats_b.health, result.final_hp_b
    )
    # ВАЖНО: health_updated_at обязательно двигать ВМЕСТЕ с health - иначе
    # следующий materialize_passive_stats (GhoulService.get) пересчитает
    # реген от СТАРОЙ метки времени поверх уже честно списанного урона и
    # может утащить здоровье обратно к максимуму, если та метка была
    # достаточно старой (найдено как реальный баг на живом тесте - у
    # победителя HP "магически" вернулось на полное после боя). Тот же
    # инвариант, что materialize_passive_stats сама соблюдает при
    # собственной записи (см. ghoul.py).
    now = utcnow_naive()
    await services.ghoul_service.set_fields(
        duel_session.initiator_telegram_id, health=new_health_a, health_updated_at=now
    )
    await services.ghoul_service.set_fields(
        duel_session.target_telegram_id, health=new_health_b, health_updated_at=now
    )

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
        reward_level_progress = (
            1.0 * loser_power / winner_power if winner_power > 0 else 0.0
        )
        await services.level_up_service.add_progress(
            winner_telegram_id, reward_level_progress
        )

    rich_message = services.battle_text_generator.build_rich_message(
        result, fighter_a, fighter_b, rank_a, rank_b
    )
    keyboard = (
        outcome_keyboard(duel_session.id, winner_telegram_id)
        if winner_telegram_id
        else None
    )

    fallback_text: Optional[str] = None

    async def _announce(chat_id: int):
        nonlocal fallback_text
        try:
            return await bot.send_rich_message(
                chat_id=chat_id, rich_message=rich_message, reply_markup=keyboard
            )
        except TelegramAPIError:
            if fallback_text is None:
                fallback_text = services.battle_text_generator.build_plain_text(
                    result, fighter_a, fighter_b, rank_a, rank_b
                )
            try:
                return await bot.send_message(
                    chat_id=chat_id, text=fallback_text, reply_markup=keyboard
                )
            except TelegramAPIError:
                logger.warning(
                    "duel %s: failed to announce fight result to %s",
                    duel_session.id,
                    chat_id,
                )
                return None

    sent = None
    if duel_session.is_private_origin:
        # ЛС инициатора и ЛС соперника - РАЗНЫЕ, невидимые друг другу
        # чаты (найдено как баг при ревью) - дублируем лог боя в оба.
        # message_id не трекаем (в отличие от группового случая) - в
        # приватном происхождении не пытаемся дальше редактировать/убирать
        # клавиатуру исхода, это чисто косметика.
        for chat_id in (
            duel_session.initiator_telegram_id,
            duel_session.target_telegram_id,
        ):
            await _announce(chat_id)
    else:
        sent = await _announce(duel_session.chat_id)

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
        return await services.duel_service.atomic_update(
            duel_session.id, "running", stage="done"
        )

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

    winner_user = await services.user_service.get(find_by=winner_id)
    loser_user = await services.user_service.get(find_by=loser_id)
    winner_name = winner_user.full_name if winner_user else str(winner_id)
    loser_name = loser_user.full_name if loser_user else str(loser_id)

    reward_rc: Optional[int] = None
    reward_balance: Optional[int] = None

    if action == "outcome_rob":
        if loser_user and loser_user.balance > 0:
            percent = random.uniform(
                DUEL_CONFIG.rob_percent_min, DUEL_CONFIG.rob_percent_max
            )
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
                * random.uniform(
                    DUEL_CONFIG.eat_rc_multiplier_min, DUEL_CONFIG.eat_rc_multiplier_max
                )
            )
            if rc > 0:
                await services.ghoul_service.increment_fields(winner_id, rc_money=rc)
                reward_rc = rc
        await services.ghoul_service.apply_death(
            loser_id, cause="eaten", killer_telegram_id=winner_id
        )

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

    if duel_session.outcome_message_id:
        try:
            await bot.edit_message_reply_markup(
                chat_id=duel_session.chat_id,
                message_id=duel_session.outcome_message_id,
                reply_markup=None,
            )
        except TelegramAPIError:
            pass

    if action == "outcome_rob":
        outcome_text = (
            f"💰 {winner_name} ограбил {loser_name} и забрал {reward_balance} CheSton's!"
            if reward_balance
            else f"💰 {winner_name} попытался ограбить {loser_name}, но у тот оказался ебаный бомж и у нечего взять."
        )
    elif action == "outcome_eat":
        outcome_text = (
            f"🍖 {winner_name} нещадно добил и сожрал {loser_name}, получив {reward_rc} RC-клеток"
            if reward_rc
            else f"🍖 {winner_name} нещадно добил и сожрал {loser_name}, но в его теле не оказалось пригодных для переваривания RC клеток"
        )
    else:
        outcome_text = f"🕊️ {winner_name} решил отпустить {loser_name}."

    if duel_session.reward_level_progress is not None:
        outcome_text += f"\n\n📈 {winner_name} получил {duel_session.reward_level_progress:.2f}% опыта за победу."

    # Счётчики побед/поражений (BATTLE_ENGINE.md 5.2) - запрашиваются
    # ПОСЛЕ record_duel выше, поэтому уже учитывают этот самый бой.
    winner_wins = await services.battle_record_service.count_wins(winner_id)
    winner_losses = await services.battle_record_service.count_losses(winner_id)
    winner_total = await services.battle_record_service.count_total_battles(winner_id)
    loser_wins = await services.battle_record_service.count_wins(loser_id)
    loser_losses = await services.battle_record_service.count_losses(loser_id)
    loser_total = await services.battle_record_service.count_total_battles(loser_id)
    outcome_text += (
        f"\n\n📊 {winner_name}: {winner_total} боёв ({winner_wins}П/{winner_losses})"
        f"\n📊 {loser_name}: {loser_total} боёв ({loser_wins}П/{loser_losses})"
    )

    # Всегда дублируем итог в ЛС обоим участникам (не только тому, кто на
    # неё нажал) - чтобы бой можно было найти в переписке в любой момент,
    # даже если исходное сообщение с логом боя потерялось в истории чата
    # (решено в чате). В приватном происхождении это и так единственная
    # доставка - `chat_id` совпадает с одним из личных чатов, добавлять
    # его отдельно незачем.
    target_chat_ids = {
        duel_session.initiator_telegram_id,
        duel_session.target_telegram_id,
    }
    if not duel_session.is_private_origin:
        target_chat_ids.add(duel_session.chat_id)

    for chat_id in target_chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=outcome_text)
        except TelegramAPIError:
            pass


__all__ = ["run_and_announce_fight", "finalize_outcome"]
