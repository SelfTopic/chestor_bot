"""Роутер PvP-дуэлей - от команды до записи в историю. Весь боевой движок
и персистентность (`BattleService`, `BattleRecordService`, `ActiveBattle`/
`Battle`) уже готовы - этот файл только связывает их в реальный Telegram-
флоу с несколькими асинхронными шагами ожидания:

1. `дуэль` (реплай/`@username`) - приглашение с ДВУМЯ кнопками (одна для
   инициатора, вторая для ответчика - сама команда ещё не согласие).
   Таймаут 1 минута -> авто-отказ.
2. Если оба согласились и перевес сил >= `DUEL_CONFIG.power_ratio_threshold` -
   сильной стороне в ЛС выбор "всерьёз/дать фору" (секретно от слабого,
   см. BATTLE_ENGINE.md 1.5). Таймаут 30 секунд -> авто-фора.
3. Сам бой - лог публикуется в ТОМ ЖЕ чате, где вызвана дуэль (не в ЛС),
   чтобы все участники чата видели, как дрались и кто победил.
4. Победителю (тоже в чате, не в ЛС) - выбор "ограбить/отпустить/съесть".
   Таймаут 1 минута -> авто-"отпустить".

Таймауты реализованы фоновыми `asyncio`-задачами (`asyncio.create_task`),
а НЕ через `scheduled_notifications`/`NotificationTicker` - та
инфраструктура заточена под "один слот на (юзер, тип уведомления), без
payload, poll раз в 30с, просто уведомить", а не под "выполнить дефолтное
действие с полным контекстом конкретной дуэли". Гонка "нажатие кнопки
против сработавшего таймаута" закрывается не блокировками в коде, а
атомарным `DuelSessionRepository.atomic_update` (UPDATE ... WHERE
stage=expected RETURNING) - выигрывает только один из двух.

Важно: `DatabaseMiddleware` коммитит и ЗАКРЫВАЕT сессию сразу после
возврата из хендлера (см. `database_middleware.py`) - поэтому фоновые
таймаут-задачи НЕ могут переиспользовать DI-инжектированные сервисы
хендлера (их сессия к моменту срабатывания таймера уже мертва). Они
открывают СОБСТВЕННУЮ сессию через `session_factory` и строят сервисы
заново - тот же приём, что уже использует `NotificationTicker._tick`."""

import asyncio
import logging
import random
from typing import NamedTuple, Optional, Tuple

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dependency_injector.wiring import Provide, inject
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import session_factory
from src.database.models import DuelSession

from ...containers import Container
from ...exceptions import (
    FighterHasPendingBattleError,
    FighterIsDeadError,
    FighterNotCombatReadyError,
)
from ...filters import Text
from ...game_configs import DUEL_CONFIG
from ...repositories import (
    ActiveBattleRepository,
    BattleRepository,
    ChatRepository,
    DeathLogRepository,
    DuelSessionRepository,
    GhoulRepository,
    ScheduledNotificationRepository,
    UserCooldownRepository,
    UserRepository,
)
from ...repositories.balances_log import BalancesLogRepository
from ...services import (
    BattleRecordService,
    BattleService,
    BattleTextGenerator,
    DialogService,
    DuelService,
    GhoulService,
    LevelUpService,
    MobService,
    UserService,
)

router = Router(name=__name__)
logger = logging.getLogger(__name__)

_VALID_ACTIONS = {
    "consent_initiator",
    "consent_target",
    "fora_serious",
    "fora_handicap",
    "outcome_rob",
    "outcome_release",
    "outcome_eat",
}

# Сильная ссылка на фоновые задачи - иначе event loop может собрать их
# сборщиком мусора до завершения (asyncio.create_task не хранит ссылку
# сам, это известная ловушка).
_background_tasks: set = set()


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def parse_duel_callback_payload(payload: str) -> Optional[Tuple[int, str, int]]:
    """Разбирает "duel:<duel_id>:<action>:<expected_telegram_id>" ->
    (duel_id, action, expected_telegram_id), или None при любом
    несоответствии формата. Вынесено в чистую функцию специально ради
    юнит-теста - тот же приём, что `parse_kagune_callback_payload` в
    `upgrade_kagune.py` (единственное, что защищает кнопку от нажатия не
    тем участником)."""

    parts = payload.split(":")
    if len(parts) != 4 or parts[0] != "duel":
        return None

    _, duel_id_str, action, expected_id_str = parts
    if not duel_id_str.isdigit() or not expected_id_str.isdigit():
        return None
    if action not in _VALID_ACTIONS:
        return None

    return int(duel_id_str), action, int(expected_id_str)


def _consent_keyboard(duel_id: int, initiator_id: int, target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтверждаю вызов (инициатор)",
                    callback_data=f"duel:{duel_id}:consent_initiator:{initiator_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚔️ Принимаю бой",
                    callback_data=f"duel:{duel_id}:consent_target:{target_id}",
                )
            ],
        ]
    )


def _fora_keyboard(duel_id: int, favored_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚔️ Всерьёз", callback_data=f"duel:{duel_id}:fora_serious:{favored_id}"
                ),
                InlineKeyboardButton(
                    text="🤝 Дать фору",
                    callback_data=f"duel:{duel_id}:fora_handicap:{favored_id}",
                ),
            ]
        ]
    )


def _outcome_keyboard(duel_id: int, winner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Ограбить", callback_data=f"duel:{duel_id}:outcome_rob:{winner_id}"
                ),
                InlineKeyboardButton(
                    text="🕊️ Отпустить",
                    callback_data=f"duel:{duel_id}:outcome_release:{winner_id}",
                ),
                InlineKeyboardButton(
                    text="🍖 Съесть", callback_data=f"duel:{duel_id}:outcome_eat:{winner_id}"
                ),
            ]
        ]
    )


class _Services(NamedTuple):
    """Пучок сервисов, нужных для проведения дуэли целиком - и в живом
    хендлере (DI-инжектированные), и в фоновой таймаут-задаче (собранные
    вручную от свежей сессии, см. `_build_services`). Единая форма ради
    того, чтобы `_run_and_announce_fight`/`_finalize_outcome` не знали, из
    какого из двух контекстов их вызвали."""

    user_service: UserService
    ghoul_service: GhoulService
    battle_service: BattleService
    battle_text_generator: BattleTextGenerator
    level_up_service: LevelUpService
    battle_record_service: BattleRecordService
    duel_service: DuelService


def _build_services(session: AsyncSession, bot: Bot) -> _Services:
    """Тот же приём, что `NotificationTicker._tick` - строит сервисы
    вручную от СВЕЖЕЙ сессии, а не переиспользует DI-контейнер (см.
    докстринг модуля про закрытие сессии `DatabaseMiddleware`)."""

    user_repository = UserRepository(session)
    ghoul_repository = GhoulRepository(session)
    user_cooldown_repository = UserCooldownRepository(session)
    chat_repository = ChatRepository(session)
    balances_log_repository = BalancesLogRepository(session)

    user_service = UserService(
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
        balances_log_repository,
    )
    ghoul_service = GhoulService(
        user_repository,
        ghoul_repository,
        user_cooldown_repository,
        chat_repository,
        notification_repository=ScheduledNotificationRepository(session),
        death_log_repository=DeathLogRepository(session),
    )
    dialog_service = DialogService()
    battle_service = BattleService(mob_service=MobService())
    battle_text_generator = BattleTextGenerator(dialog_service=dialog_service)
    level_up_service = LevelUpService(
        user_service=user_service,
        ghoul_service=ghoul_service,
        dialog_service=dialog_service,
        bot=bot,
    )
    battle_record_service = BattleRecordService(
        active_battle_repository=ActiveBattleRepository(session),
        battle_repository=BattleRepository(session),
    )
    duel_service = DuelService(DuelSessionRepository(session))

    return _Services(
        user_service=user_service,
        ghoul_service=ghoul_service,
        battle_service=battle_service,
        battle_text_generator=battle_text_generator,
        level_up_service=level_up_service,
        battle_record_service=battle_record_service,
        duel_service=duel_service,
    )


# --- Шаг 1: приглашение -----------------------------------------------------


@router.message(Text("дуэль", startswith=True))
@inject
async def duel_invite_handler(
    message: Message,
    bot: Bot,
    user_service: UserService = Provide[Container.user_service],
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    battle_service: BattleService = Provide[Container.battle_service],
    battle_record_service: BattleRecordService = Provide[Container.battle_record_service],
    duel_service: DuelService = Provide[Container.duel_service],
) -> None:
    if not message.from_user or not message.text:
        return None

    initiator_id = message.from_user.id

    reply = message.reply_to_message
    if reply and reply.from_user:
        target_id = reply.from_user.id
    else:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "Вызови реплаем на сообщение соперника, либо «дуэль @username» / «дуэль <id>»."
            )
            return None

        query = args[1].strip()
        search = int(query) if query.lstrip("-").isdigit() else query.lstrip("@")
        target_user = await user_service.get(find_by=search)
        if not target_user:
            await message.reply(f"Пользователь не найден: {query}")
            return None
        target_id = target_user.telegram_id

    if target_id == initiator_id:
        await message.reply("Нельзя вызвать на дуэль самого себя.")
        return None

    initiator_user = await user_service.get(find_by=initiator_id)
    target_user = await user_service.get(find_by=target_id)
    if not initiator_user or not target_user:
        await message.reply("Один из участников не зарегистрирован.")
        return None

    if not initiator_user.has_private_chat or not target_user.has_private_chat:
        who = "Тебе" if not initiator_user.has_private_chat else "Сопернику"
        await message.reply(
            f"{who} нужно один раз написать боту в ЛС (подойдёт /start) - иначе "
            f"часть сообщений о бое некуда будет доставить."
        )
        return None

    initiator_ghoul = await ghoul_service.get(initiator_id)
    target_ghoul = await ghoul_service.get(target_id)
    if not initiator_ghoul:
        await message.reply("У тебя ещё нет гуля.")
        return None
    if not target_ghoul:
        await message.reply("У соперника ещё нет гуля.")
        return None

    try:
        await battle_service.validate_duel(
            initiator_ghoul,
            target_ghoul,
            has_pending_confirmation=lambda g: battle_record_service.is_busy(g.telegram_id),
        )
    except FighterIsDeadError:
        await message.reply("Один из участников мёртв.")
        return None
    except FighterNotCombatReadyError as exc:
        await message.reply(
            f"Один из участников небоеспособен: {exc.health} HP "
            f"(нужно минимум {exc.threshold})."
        )
        return None
    except FighterHasPendingBattleError:
        await message.reply("Один из участников уже занят другим боем.")
        return None

    if (
        await battle_record_service.count_pair_last_24h(initiator_id, target_id)
        >= DUEL_CONFIG.max_battles_per_day_pair
    ):
        await message.reply(
            f"Лимит боёв с этим соперником на сегодня исчерпан "
            f"({DUEL_CONFIG.max_battles_per_day_pair}/сутки)."
        )
        return None
    if (
        await battle_record_service.count_total_last_24h(initiator_id)
        >= DUEL_CONFIG.max_battles_per_day_total
    ):
        await message.reply(
            f"Твой дневной лимит боёв исчерпан ({DUEL_CONFIG.max_battles_per_day_total}/сутки)."
        )
        return None
    if (
        await battle_record_service.count_total_last_24h(target_id)
        >= DUEL_CONFIG.max_battles_per_day_total
    ):
        await message.reply("У соперника исчерпан дневной лимит боёв на сегодня.")
        return None

    if not await battle_record_service.try_claim_duel(initiator_id, target_id):
        await message.reply("Не удалось начать дуэль - один из участников уже занят.")
        return None

    duel_session = await duel_service.create(
        chat_id=message.chat.id,
        initiator_telegram_id=initiator_id,
        target_telegram_id=target_id,
    )

    sent = await message.answer(
        f"⚔️ {initiator_user.full_name} вызывает {target_user.full_name} на дуэль!\n"
        f"Бой начнётся только после подтверждения ОБЕИХ сторон.",
        reply_markup=_consent_keyboard(duel_session.id, initiator_id, target_id),
    )
    await duel_service.atomic_update(
        duel_session.id, "awaiting_consent", consent_message_id=sent.message_id
    )

    _spawn(_expire_consent(bot, duel_session.id))
    return None


# --- Общая логика боя/исхода (используется и живым колбэком, и таймаутами) --


async def _run_and_announce_fight(
    bot: Bot, duel_session: DuelSession, services: _Services
) -> None:
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
        return

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
        reward_level_progress = (
            1.0 * loser_power / winner_power if winner_power > 0 else 0.0
        )
        await services.level_up_service.add_progress(winner_telegram_id, reward_level_progress)

    rich_message = services.battle_text_generator.build_rich_message(
        result, fighter_a, fighter_b, rank_a, rank_b
    )
    keyboard = _outcome_keyboard(duel_session.id, winner_telegram_id) if winner_telegram_id else None

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
        await services.duel_service.atomic_update(duel_session.id, "running", stage="done")
        return

    await services.duel_service.atomic_update(
        duel_session.id,
        "running",
        stage="awaiting_winner_choice",
        winner_telegram_id=winner_telegram_id,
        loser_telegram_id=loser_telegram_id,
        outcome_message_id=sent.message_id if sent else None,
        reward_level_progress=reward_level_progress,
        ended_naturally=result.ended_naturally,
    )
    _spawn(_expire_outcome(bot, duel_session.id))


async def _finalize_outcome(
    bot: Bot, duel_session: DuelSession, action: str, services: _Services
) -> None:
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


# --- Шаг 2/3/5: колбэки живых кнопок -----------------------------------------


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

    services = _Services(
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
    callback_query: CallbackQuery, bot: Bot, duel_id: int, action: str, services: _Services
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
                    reply_markup=_consent_keyboard(
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
        await _run_and_announce_fight(bot, session, services)
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
            reply_markup=_fora_keyboard(duel_id, favored_id),
        )
    except TelegramAPIError:
        logger.warning("duel %s: failed to DM fora choice", duel_id)

    _spawn(_expire_fora(bot, duel_id))


async def _handle_fora(
    callback_query: CallbackQuery, bot: Bot, duel_id: int, action: str, services: _Services
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

    await _run_and_announce_fight(bot, session, services)


async def _handle_outcome(
    callback_query: CallbackQuery, bot: Bot, duel_id: int, action: str, services: _Services
) -> None:
    session = await services.duel_service.atomic_update(
        duel_id, "awaiting_winner_choice", stage="done", winner_choice=action
    )
    if not session:
        await callback_query.answer("Уже неактуально.", show_alert=True)
        return

    await callback_query.answer("Принято!")
    await _finalize_outcome(bot, session, action, services)


# --- Фоновые таймауты --------------------------------------------------------


async def _expire_consent(bot: Bot, duel_id: int) -> None:
    await asyncio.sleep(DUEL_CONFIG.invite_timeout_seconds)
    try:
        async with session_factory() as session:
            services = _build_services(session, bot)
            updated = await services.duel_service.atomic_update(
                duel_id, "awaiting_consent", stage="done"
            )
            if not updated:
                return
            await services.battle_record_service.release(
                updated.initiator_telegram_id, updated.target_telegram_id
            )
            await session.commit()

        if updated.consent_message_id:
            try:
                await bot.edit_message_text(
                    chat_id=updated.chat_id,
                    message_id=updated.consent_message_id,
                    text="⌛ Время на согласие вышло - дуэль отменена.",
                )
            except TelegramAPIError:
                pass
    except Exception:
        logger.exception("duel %s: consent expiry failed", duel_id)


async def _expire_fora(bot: Bot, duel_id: int) -> None:
    await asyncio.sleep(DUEL_CONFIG.serious_or_handicap_timeout_seconds)
    try:
        async with session_factory() as session:
            services = _build_services(session, bot)
            updated = await services.duel_service.atomic_update(
                duel_id, "awaiting_serious_or_handicap", stage="running", compress_hp=True
            )
            if not updated:
                return
            await _run_and_announce_fight(bot, updated, services)
            await session.commit()
    except Exception:
        logger.exception("duel %s: fora expiry failed", duel_id)


async def _expire_outcome(bot: Bot, duel_id: int) -> None:
    await asyncio.sleep(DUEL_CONFIG.winner_choice_timeout_seconds)
    try:
        async with session_factory() as session:
            services = _build_services(session, bot)
            updated = await services.duel_service.atomic_update(
                duel_id, "awaiting_winner_choice", stage="done", winner_choice="outcome_release"
            )
            if not updated:
                return
            await _finalize_outcome(bot, updated, "outcome_release", services)
            await session.commit()
    except Exception:
        logger.exception("duel %s: outcome expiry failed", duel_id)


__all__ = ["router", "parse_duel_callback_payload"]
