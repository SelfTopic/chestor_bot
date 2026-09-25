"""
"Разыграть бой и объявить результат" и "применить выбор победителя": общее для
живых нажатий (callbacks.py) и таймаутов (ticker.py), поэтому получает только Bot и
DuelServices. Логика перенесена из прод-fight.py как есть, включая тексты.

Как у прода, у дуэли из лички (is_private_origin) лог боя и итог дублируются в оба
личных чата, а id сообщения с кнопками исхода не запоминается: там клавиатуру
после выбора не убираем.
"""

import logging
import random

from selfrot import Bot
from selfrot.exceptions import TelegramAPIError
from selfrot.types import Message

from src.bot.game_configs import DUEL_CONFIG
from src.bot.services import BattleService
from src.bot.utils import utcnow_naive
from src.database.models import DuelSession

from ..battle_text import battle_rich
from .keyboards import outcome_keyboard
from .services import DuelServices

logger = logging.getLogger(__name__)


async def run_and_announce_fight(
    bot: Bot, duel_session: DuelSession, services: DuelServices
) -> DuelSession | None:
    """Итоговое состояние DuelSession после боя; None, если участник исчез между
    шагами (страховка). Стадия "awaiting_winner_choice" в ответе значит, что ждём
    выбор победителя; его таймаут ведёт DuelTicker."""
    ghoul_service = services.ghoul_service
    battle_service = services.battle_service

    initiator_ghoul = await ghoul_service.get(duel_session.initiator_telegram_id)
    target_ghoul = await ghoul_service.get(duel_session.target_telegram_id)
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

    fighter_a = battle_service.ghoul_to_fighter(
        initiator_ghoul, initiator_user.full_name, ghoul_service
    )
    fighter_b = battle_service.ghoul_to_fighter(
        target_ghoul, target_user.full_name, ghoul_service
    )

    compress_hp = (
        duel_session.compress_hp if duel_session.compress_hp is not None else True
    )
    result = battle_service.run_duel(fighter_a, fighter_b, compress_hp=compress_hp)

    new_health_a = BattleService.resolve_post_battle_health(
        initiator_ghoul.health, result.stats_a.health, result.final_hp_a
    )
    new_health_b = BattleService.resolve_post_battle_health(
        target_ghoul.health, result.stats_b.health, result.final_hp_b
    )
    # health_updated_at двигается вместе с health: иначе следующий
    # materialize_passive_stats досчитает реген от старой метки поверх урона.
    now = utcnow_naive()
    await ghoul_service.set_fields(
        duel_session.initiator_telegram_id, health=new_health_a, health_updated_at=now
    )
    await ghoul_service.set_fields(
        duel_session.target_telegram_id, health=new_health_b, health_updated_at=now
    )

    rank_a = ghoul_service.get_danger_rank(battle_service.power_of(fighter_a.snapshot))
    rank_b = ghoul_service.get_danger_rank(battle_service.power_of(fighter_b.snapshot))

    winner_telegram_id: int | None = None
    loser_telegram_id: int | None = None
    reward_level_progress: float | None = None

    if result.winner is not None:
        is_initiator_winner = result.winner == "a"
        winner_telegram_id, loser_telegram_id = (
            (duel_session.initiator_telegram_id, duel_session.target_telegram_id)
            if is_initiator_winner
            else (duel_session.target_telegram_id, duel_session.initiator_telegram_id)
        )
        winner_ghoul, loser_ghoul = (
            (initiator_ghoul, target_ghoul)
            if is_initiator_winner
            else (target_ghoul, initiator_ghoul)
        )
        winner_power = ghoul_service.calculate_power(winner_ghoul)
        loser_power = ghoul_service.calculate_power(loser_ghoul)
        # Формула левел-апа (BATTLE_DESIGN.md): 1% * (сила соперника / своя сила).
        reward_level_progress = (
            1.0 * loser_power / winner_power if winner_power > 0 else 0.0
        )
        await services.level_up_service.add_progress(
            winner_telegram_id, reward_level_progress
        )

    generator = services.battle_text_generator
    rich_message = battle_rich(generator, result, fighter_a, fighter_b, rank_a, rank_b)
    keyboard = (
        outcome_keyboard(duel_session.id, winner_telegram_id)
        if winner_telegram_id
        else None
    )
    fallback_text: str | None = None

    async def announce(chat_id: int) -> Message | None:
        nonlocal fallback_text
        try:
            return await bot.send_rich_message(
                chat_id=chat_id, rich_message=rich_message, reply_markup=keyboard
            )
        except TelegramAPIError:
            if fallback_text is None:
                fallback_text = generator.build_plain_text(
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
        for chat_id in (
            duel_session.initiator_telegram_id,
            duel_session.target_telegram_id,
        ):
            await announce(chat_id)
    else:
        sent = await announce(duel_session.chat_id)

    if winner_telegram_id is None or loser_telegram_id is None:
        # Настоящая ничья (BATTLE_ENGINE.md 2.6): выбирать нечего, история сразу.
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
    bot: Bot, duel_session: DuelSession, action: str, services: DuelServices
) -> None:
    """Исход "ограбить/отпустить/съесть". Вызывать только после того, как
    atomic_update реально перевёл сессию в "done" с этим выбором: из гонки нажатия
    и таймаута сюда попадает только победитель."""
    assert duel_session.winner_telegram_id is not None
    assert duel_session.loser_telegram_id is not None
    winner_id = duel_session.winner_telegram_id
    loser_id = duel_session.loser_telegram_id
    user_service = services.user_service
    ghoul_service = services.ghoul_service
    battles = services.battle_record_service

    winner_user = await user_service.get(find_by=winner_id)
    loser_user = await user_service.get(find_by=loser_id)
    winner_name = winner_user.full_name if winner_user else str(winner_id)
    loser_name = loser_user.full_name if loser_user else str(loser_id)

    reward_rc: int | None = None
    reward_balance: int | None = None
    hunger_restored: int | None = None

    if action == "outcome_rob":
        if loser_user and loser_user.balance > 0:
            percent = random.uniform(
                DUEL_CONFIG.rob_percent_min, DUEL_CONFIG.rob_percent_max
            )
            amount = round(loser_user.balance * percent / 100.0)
            if amount > 0:
                await user_service.minus_balance(
                    loser_id, amount, log=f"duel robbery by {winner_id}"
                )
                await user_service.plus_balance(
                    winner_id, amount, log=f"duel robbery from {loser_id}"
                )
                reward_balance = amount
    elif action == "outcome_eat":
        loser_ghoul = await ghoul_service.get(loser_id)
        if loser_ghoul:
            power = ghoul_service.calculate_power(loser_ghoul)
            rc = round(
                power
                * random.uniform(
                    DUEL_CONFIG.eat_rc_multiplier_min, DUEL_CONFIG.eat_rc_multiplier_max
                )
            )
            if rc > 0:
                await ghoul_service.increment_fields(winner_id, rc_money=rc)
                reward_rc = rc
        await ghoul_service.apply_death(
            loser_id, cause="eaten", killer_telegram_id=winner_id
        )
        # apply_death трогает только проигравшего: счётчик съеденных гулей и голод
        # победителя ведутся отдельно (те же проценты, что у "сожрать человека").
        await ghoul_service.increment_fields(winner_id, eat_ghouls=1)
        _, hunger_restored = await ghoul_service.restore_hunger_from_eating(winner_id)

    winner_label = "a" if winner_id == duel_session.initiator_telegram_id else "b"
    await battles.record_duel(
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
    await battles.release(
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

    # Опечатки в текстах ("у тот", "у нечего") как у прода.
    if action == "outcome_rob":
        outcome_text = (
            f"💰 {winner_name} ограбил {loser_name} и забрал {reward_balance} CheSton's!"
            if reward_balance
            else f"💰 {winner_name} попытался ограбить {loser_name}, но у тот оказался "
            "ебаный бомж и у нечего взять."
        )
    elif action == "outcome_eat":
        outcome_text = (
            f"🍖 {winner_name} нещадно добил и сожрал {loser_name}, "
            f"получив {reward_rc} RC-клеток"
            if reward_rc
            else f"🍖 {winner_name} нещадно добил и сожрал {loser_name}, но в его "
            "теле не оказалось пригодных для переваривания RC клеток"
        )
        if hunger_restored is not None:
            outcome_text += (
                f"\n🍖 Голод {winner_name} восстановлен на {hunger_restored}%."
            )
    else:
        outcome_text = f"🕊️ {winner_name} решил отпустить {loser_name}."

    if duel_session.reward_level_progress is not None:
        outcome_text += (
            f"\n\n📈 {winner_name} получил "
            f"{duel_session.reward_level_progress:.2f}% опыта за победу."
        )

    # Счёт только дуэлей (BATTLE_ENGINE.md 5.2), уже с этим боем.
    winner_wins = await battles.count_wins_vs_players(winner_id)
    winner_losses = await battles.count_losses_vs_players(winner_id)
    winner_total = await battles.count_total_battles_vs_players(winner_id)
    loser_wins = await battles.count_wins_vs_players(loser_id)
    loser_losses = await battles.count_losses_vs_players(loser_id)
    loser_total = await battles.count_total_battles_vs_players(loser_id)
    outcome_text += (
        f"\n\n📊 {winner_name}: {winner_total} боёв ({winner_wins}П/{winner_losses})"
        f"\n📊 {loser_name}: {loser_total} боёв ({loser_wins}П/{loser_losses})"
    )

    # Итог всегда дублируется в личку обоим, чтобы бой можно было найти в
    # переписке; у дуэли из лички это и есть единственная доставка.
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
