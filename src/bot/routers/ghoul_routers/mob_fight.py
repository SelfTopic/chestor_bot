"""Роутер боя с мобом - "бить моба", раз в 10 минут (кулдаун `MOB_FIGHT`,
см. миграцию `e23859132e56`). В отличие от дуэли - без согласия, без
выбора "всерьёз/фора" (BATTLE_ENGINE.md 1.5: "бои с мобами - всегда
compress_hp=True, выбора нет") и без выбора победителя "ограбить/
отпустить/съесть" (моб - не гуль, грабить/есть нечего) - бой резолвится
и объявляется одним заходом.

Использует `ActiveBattle`-лок (`try_claim_mob_fight`/`release`) ровно за
тем же, зачем и дуэль - закрывает эксплойт "одновременно дуэль и бой с
мобом" (см. чат, `BattleService.validate_ghoul(has_pending_confirmation=...)`).

Заменяет собой `mob_fight_preview.py` (был явно временным debug-
инструментом без кулдауна/персистентности - решено в чате)."""

import logging
import random
import time

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...exceptions import (
    FighterHasPendingBattleError,
    FighterIsDeadError,
    FighterNotCombatReadyError,
    GhoulNotFoundInDatabase,
)
from ...game_configs import MOB_CONFIG
from ...services import (
    BattleRecordService,
    BattleService,
    BattleTextGenerator,
    CooldownService,
    DialogService,
    GhoulService,
    LevelUpService,
    UserService,
)
from ...utils import parse_seconds, utcnow_naive

router = Router(name=__name__)
logger = logging.getLogger(__name__)

_COOLDOWN_NAME = "MOB_FIGHT"


@router.message(F.text.lower() == "бить моба")
@inject
async def mob_fight_handler(
    message: Message,
    user_service: UserService = Provide[Container.user_service],
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    battle_service: BattleService = Provide[Container.battle_service],
    battle_text_generator: BattleTextGenerator = Provide[Container.battle_text_generator],
    battle_record_service: BattleRecordService = Provide[Container.battle_record_service],
    level_up_service: LevelUpService = Provide[Container.level_up_service],
    cooldown_service: CooldownService = Provide[Container.cooldown_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
) -> None:
    if not message.from_user:
        logger.warning("User not found in message")
        return None

    telegram_id = message.from_user.id

    user = await user_service.get(find_by=telegram_id)
    if not user:
        raise ValueError("User not found in database")

    ghoul = await ghoul_service.get(message)
    if not ghoul:
        raise GhoulNotFoundInDatabase("Ghoul not found for user")

    try:
        await battle_service.validate_ghoul(
            ghoul,
            has_pending_confirmation=lambda g: battle_record_service.is_busy(g.telegram_id),
        )
    except FighterIsDeadError:
        await message.reply(text=dialog_service.text(key="dead_ghoul_reply"))
        return None
    except FighterNotCombatReadyError as exc:
        await message.reply(
            text=dialog_service.text(
                key="not_combat_ready", health=exc.health, threshold=exc.threshold
            )
        )
        return None
    except FighterHasPendingBattleError:
        await message.reply(text="Ты сейчас занят другим боем.")
        return None

    user_cooldown = await cooldown_service.get_active_cooldown(
        telegram_id=telegram_id, cooldown_name=_COOLDOWN_NAME
    )
    if user_cooldown:
        remaining = parse_seconds(total_seconds=int(user_cooldown.end_at - time.time()))
        await message.reply(
            text=(
                f"Рано - ты недавно уже дрался с мобом. Попробуй через "
                f"{remaining.minutes_remaining}м {remaining.seconds_remaining}с."
            )
        )
        return None

    if not await battle_record_service.try_claim_mob_fight(telegram_id):
        await message.reply(text="Ты сейчас занят другим боем.")
        return None

    player = battle_service.ghoul_to_fighter(ghoul, user.full_name, ghoul_service)
    result, mob = battle_service.run_against_mob(player)

    new_health = BattleService.resolve_post_battle_health(
        ghoul.health, result.stats_a.health, result.final_hp_a
    )
    await ghoul_service.set_fields(telegram_id, health=new_health, health_updated_at=utcnow_naive())

    reward_level_progress = None
    reward_rc = None

    if result.winner == "a":
        mob_power = battle_service.power_of(mob.snapshot)
        player_power = ghoul_service.calculate_power(ghoul)
        # BATTLE_DESIGN.md "Формула левел-апа" - та же 1%*(сила соперника/
        # своя сила), что и у дуэли, но ÷5 - фарм мобов медленнее PvP.
        reward_level_progress = (
            (mob_power / player_power) / MOB_CONFIG.level_progress_divisor
            if player_power > 0
            else 0.0
        )
        await level_up_service.add_progress(telegram_id, reward_level_progress)

        if random.random() < MOB_CONFIG.rc_drop_chance:
            reward_rc = random.randint(MOB_CONFIG.rc_drop_min, MOB_CONFIG.rc_drop_max)
            await ghoul_service.increment_fields(telegram_id, rc_money=reward_rc)

    await battle_record_service.record_mob_fight(
        telegram_id=telegram_id,
        mob_name=mob.name,
        winner=result.winner,
        ended_naturally=result.ended_naturally,
        is_forced=False,
        reward_level_progress=reward_level_progress,
        reward_rc=reward_rc,
    )
    await battle_record_service.release(telegram_id)
    await cooldown_service.set_cooldown(telegram_id=telegram_id, cooldown_type=_COOLDOWN_NAME)

    rank_a = ghoul_service.get_danger_rank(battle_service.power_of(player.snapshot))
    rank_b = ghoul_service.get_danger_rank(battle_service.power_of(mob.snapshot))

    rich_message = battle_text_generator.build_rich_message(result, player, mob, rank_a, rank_b)
    try:
        await message.answer_rich(rich_message=rich_message)
    except TelegramAPIError:
        logger.warning(
            "send_rich_message failed for mob fight, falling back to plain text", exc_info=True
        )
        fallback_text = battle_text_generator.build_plain_text(result, player, mob, rank_a, rank_b)
        await message.answer(text=fallback_text)

    if result.winner == "a":
        summary = f"📈 Получено опыта: {reward_level_progress:.2f}%"
        if reward_rc:
            summary += f"\n♦️ Дополнительно найдено: {reward_rc} RC-клеток!"
    elif result.winner == "b":
        summary = "Моб оказался сильнее в этот раз."
    else:
        summary = "Ничья - силы примерно равны."

    wins = await battle_record_service.count_wins(telegram_id)
    losses = await battle_record_service.count_losses(telegram_id)
    total = await battle_record_service.count_total_battles(telegram_id)
    summary += f"\n📊 Всего боёв: {total} ({wins} побед / {losses} поражений)"

    await message.answer(text=summary)
    return None


__all__ = ["router"]
