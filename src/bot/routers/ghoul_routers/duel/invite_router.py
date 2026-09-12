"""Шаг 1 - "дуэль" (реплай/`@username`) - приглашение с ДВУМЯ кнопками
(одна для инициатора, вторая для ответчика - сама команда ещё не
согласие, см. чат). Таймаут 1 минута -> авто-отказ (см. `background.py`).

Все проверки ДО отправки приглашения: жив/боеспособен/не занят другим
боем (`BattleService.validate_duel`), дневные лимиты (5/пара, 20/сутки -
см. `BATTLE_ENGINE.md` 1.2/4.4), и обе стороны должны иметь открытую ЛС с
ботом (`User.has_private_chat`) - без этого секретный шаг "всерьёз/фора"
(1.5) и часть остальных сообщений некуда доставить.

Отдельный случай - дуэль вызвана из ЛС инициатора с ботом (соперник
указан через @username, без общего группового чата). Тогда `message.chat`
- приватный чат ровно между инициатором и ботом, соперник в нём не
состоит и никогда не увидит там приглашение (найдено как баг при ревью -
Telegram ЛС не бывает "на троих"). В этом случае приглашение дублируется
в ОБА личных чата - см. `is_private_origin` на `DuelSession`."""

import logging

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ....containers import Container
from ....exceptions import (
    FighterHasPendingBattleError,
    FighterIsDeadError,
    FighterNotCombatReadyError,
)
from ....filters import Text
from ....game_configs import DUEL_CONFIG
from ....services import BattleRecordService, BattleService, DuelService, GhoulService, UserService
from .background import expire_consent, spawn
from .keyboards import consent_keyboard

router = Router(name=__name__)
logger = logging.getLogger(__name__)


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

    is_private_origin = message.chat.type == "private"
    duel_session = await duel_service.create(
        chat_id=message.chat.id,
        initiator_telegram_id=initiator_id,
        target_telegram_id=target_id,
        is_private_origin=is_private_origin,
    )

    invite_text = (
        f"⚔️ {initiator_user.full_name} вызывает {target_user.full_name} на дуэль!\n"
        f"Бой начнётся только после подтверждения ОБЕИХ сторон."
    )
    keyboard = consent_keyboard(duel_session.id, initiator_id, target_id)

    if is_private_origin:
        # ЛС инициатора с ботом не видна сопернику - дублируем
        # приглашение в его СОБСТВЕННЫЙ чат с ботом, иначе он никогда не
        # увидит кнопку "принимаю бой". Message.answer() тут не годится -
        # шлём явно в оба chat_id по отдельности, id сообщений не
        # трекаем (see fight.py - в приватном случае не редактируем эти
        # сообщения дальше, это чисто косметика).
        for chat_id in (initiator_id, target_id):
            try:
                await bot.send_message(chat_id=chat_id, text=invite_text, reply_markup=keyboard)
            except TelegramAPIError:
                logger.warning(
                    "duel %s: failed to deliver invite to %s", duel_session.id, chat_id
                )
    else:
        sent = await message.answer(invite_text, reply_markup=keyboard)
        await duel_service.atomic_update(
            duel_session.id, "awaiting_consent", consent_message_id=sent.message_id
        )

    spawn(expire_consent(bot, duel_session.id))
    return None


__all__ = ["router"]
