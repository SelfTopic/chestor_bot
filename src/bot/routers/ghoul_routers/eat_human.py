"""Команда "сожрать человека" - фазы 3a+3b из BATTLE_DESIGN.md в одном
роутере:
- 3a (было всегда): восстановление голода раз в кулдаун, без риска.
- 3b (эта версия): ПЕРЕД восстановлением голода с фиксированным шансом
  (`EAT_HUMAN_CONFIG.ambush_chance_percent`) нападает моб-гуль, тоже
  претендующий на человека - принудительный бой (без согласия и, пока,
  без попытки сбежать - см. `BattleService.run_against_mob`), голод самого
  гуля на это не влияет. Победа → доедаем человека как обычно (3a
  наступает следом); поражение/ничья - человек достаётся мобу, голод не
  восстанавливается, но кулдаун всё равно расходуется (попытка была).

Бой с мобом здесь - тот же путь, что и "бить моба" (mob_fight.py):
`ActiveBattle`-лок, `MOB_CONFIG` для наград (level_progress/RC-дроп/
CheSton), запись в историю (`battle_type="mob"`, но `is_forced=True` -
единственное отличие от добровольного mob_fight.py) и тот же рендер через
`BattleTextGenerator`."""

import logging
import random
import time

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import FSInputFile, Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...game_configs import EAT_HUMAN_CONFIG, MOB_CONFIG
from ...services import (
    BattleRecordService,
    BattleService,
    BattleTextGenerator,
    CooldownService,
    DialogService,
    GhoulService,
    LevelUpService,
    MediaService,
    UserService,
)
from ...utils import parse_seconds, utcnow_naive

router = Router(name=__name__)

logger = logging.getLogger(__name__)

COOLDOWN_NAME = "EAT_HUMAN"


@router.message(F.text.lower() == "сожрать человека")
@inject
async def eat_human_handler(
    message: Message,
    user_service: UserService = Provide[Container.user_service],
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    battle_service: BattleService = Provide[Container.battle_service],
    battle_text_generator: BattleTextGenerator = Provide[Container.battle_text_generator],
    battle_record_service: BattleRecordService = Provide[Container.battle_record_service],
    level_up_service: LevelUpService = Provide[Container.level_up_service],
    cooldown_service: CooldownService = Provide[Container.cooldown_service],
    dialog_service: DialogService = Provide[Container.dialog_service],
    media_service: MediaService = Provide[Container.media_service],
) -> None:
    if not message.from_user:
        logger.warning("User not found")
        return None

    telegram_id = message.from_user.id

    user_cooldown = await cooldown_service.get_active_cooldown(
        telegram_id=telegram_id, cooldown_name=COOLDOWN_NAME
    )

    if user_cooldown:
        cooldown_remaining = parse_seconds(
            total_seconds=int(user_cooldown.end_at - time.time())
        )
        await message.reply(
            text=dialog_service.text(
                key="eat_human_cooldown_error",
                hours=cooldown_remaining.total_hours,
                minutes=cooldown_remaining.minutes_remaining,
                seconds=cooldown_remaining.seconds_remaining,
            )
        )
        return None

    # 3b - фиксированный шанс, независимый от голода/статов. Если лок уже
    # занят (тот же ActiveBattle, что и у дуэли/mob_fight.py) - считаем,
    # что засады не случилось, а не блокируем еду целиком.
    rolled_ambush = random.random() * 100 < EAT_HUMAN_CONFIG.ambush_chance_percent
    ambushed = rolled_ambush and await battle_record_service.try_claim_mob_fight(telegram_id)

    if ambushed:
        survived = await _resolve_ambush(
            message,
            telegram_id,
            user_service=user_service,
            ghoul_service=ghoul_service,
            battle_service=battle_service,
            battle_text_generator=battle_text_generator,
            battle_record_service=battle_record_service,
            level_up_service=level_up_service,
        )
        # Кулдаун расходуется в любом случае - попытка поесть уже была,
        # независимо от исхода боя.
        await cooldown_service.set_cooldown(telegram_id=telegram_id, cooldown_type=COOLDOWN_NAME)

        if not survived:
            return None
        # Победил - доедаем человека ниже, как в обычном 3a.

    ghoul, restored = await ghoul_service.eat_human(telegram_id=telegram_id)

    if not ambushed:
        await cooldown_service.set_cooldown(telegram_id=telegram_id, cooldown_type=COOLDOWN_NAME)

    caption = dialog_service.text(
        key="eat_human_accept",
        restored=restored,
        hunger=ghoul.hunger,
        count=ghoul.eat_humans,
    )

    media = await media_service.get_random_gif(
        "eat human", user_id=telegram_id
    )

    if not media:
        await message.reply(text=caption)
        return None

    logger.debug(f"Media path: {media.path}, media file_id: {media.telegram_file_id}")

    try:
        await message.reply_animation(
            animation=media.telegram_file_id or FSInputFile(media.path),
            caption=caption,
        )

    except TelegramBadRequest:
        my_message = await message.reply_animation(
            animation=FSInputFile(media.path), caption=caption
        )

        if not my_message.animation:
            raise
        await media_service.update_telegram_file_id(
            path=media.path, new_file_id=my_message.animation.file_id
        )

    return None


async def _resolve_ambush(
    message: Message,
    telegram_id: int,
    *,
    user_service: UserService,
    ghoul_service: GhoulService,
    battle_service: BattleService,
    battle_text_generator: BattleTextGenerator,
    battle_record_service: BattleRecordService,
    level_up_service: LevelUpService,
) -> bool:
    """Принудительный бой с мобом за право доесть человека. Возвращает
    True, если игрок победил (можно продолжать 3a), False - проиграл или
    ничья (человек достался мобу). Лок (`try_claim_mob_fight`) уже занят
    вызывающим кодом - здесь только сам бой, награды, запись и рендер;
    release тоже делается здесь (жизненный цикл лока целиком в этой
    функции, симметрично claim/release в mob_fight.py)."""

    user = await user_service.get(find_by=telegram_id)
    if not user:
        raise ValueError("User not found in database")

    ghoul = await ghoul_service.get(message)
    if not ghoul:
        raise ValueError("Ghoul not found")

    player = battle_service.ghoul_to_fighter(ghoul, user.full_name, ghoul_service)
    result, mob = battle_service.run_against_mob(player)

    new_health = BattleService.resolve_post_battle_health(
        ghoul.health, result.stats_a.health, result.final_hp_a
    )
    await ghoul_service.set_fields(
        telegram_id, health=new_health, health_updated_at=utcnow_naive()
    )

    reward_level_progress = None
    reward_rc = None
    reward_cheston = None

    if result.winner == "a":
        mob_power = battle_service.power_of(mob.snapshot)
        player_power = ghoul_service.calculate_power(ghoul)
        # Та же формула левел-апа, что у "бить моба" (BATTLE_DESIGN.md).
        reward_level_progress = (
            (mob_power / player_power) / MOB_CONFIG.level_progress_divisor
            if player_power > 0
            else 0.0
        )
        await level_up_service.add_progress(telegram_id, reward_level_progress)

        if random.random() < MOB_CONFIG.rc_drop_chance:
            reward_rc = random.randint(MOB_CONFIG.rc_drop_min, MOB_CONFIG.rc_drop_max)
            await ghoul_service.increment_fields(telegram_id, rc_money=reward_rc)

        reward_cheston = MOB_CONFIG.cheston_reward_for_mob_win(ghoul.level)
        await user_service.plus_balance(
            telegram_id, change_balance=reward_cheston, log="mob ambush during eat_human reward"
        )

    await battle_record_service.record_mob_fight(
        telegram_id=telegram_id,
        mob_name=mob.name,
        winner=result.winner,
        ended_naturally=result.ended_naturally,
        is_forced=True,
        reward_level_progress=reward_level_progress,
        reward_rc=reward_rc,
        reward_balance=reward_cheston,
    )
    await battle_record_service.release(telegram_id)

    rank_a = ghoul_service.get_danger_rank(battle_service.power_of(player.snapshot))
    rank_b = ghoul_service.get_danger_rank(battle_service.power_of(mob.snapshot))

    await message.reply(
        text="🐺 Пока ты подкрадывался к добыче, из темноты выскочил другой "
        "гуль, тоже претендующий на человека - придётся драться!"
    )

    rich_message = battle_text_generator.build_rich_message(result, player, mob, rank_a, rank_b)
    try:
        await message.answer_rich(rich_message=rich_message)
    except TelegramAPIError:
        logger.warning(
            "send_rich_message failed for mob ambush during eat_human, falling back to plain text",
            exc_info=True,
        )
        fallback_text = battle_text_generator.build_plain_text(result, player, mob, rank_a, rank_b)
        await message.answer(text=fallback_text)

    if result.winner == "a":
        summary = f"📈 Получено опыта: {reward_level_progress:.2f}%"
        summary += f"\n💰 Получено CheSton: {reward_cheston}"
        if reward_rc:
            summary += f"\n♦️ Дополнительно найдено: {reward_rc} RC-клеток!"
        summary += "\n\n🍽 Соперник повержен - человек твой."
        await message.answer(text=summary)
        return True

    if result.winner == "b":
        await message.answer(text="Моб оказался сильнее - человек достался ему.")
    else:
        await message.answer(text="Ничья - в суматохе добыча сбежала, поесть не вышло.")

    return False


__all__ = ["router"]
