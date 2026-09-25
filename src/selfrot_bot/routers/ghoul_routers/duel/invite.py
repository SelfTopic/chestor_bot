"""
Шаг 1, "дуэль": приглашение с двумя кнопками (для инициатора и для соперника: сама
команда ещё не согласие). Таймаут согласия ведёт DuelTicker.

До приглашения проверяется всё: оба живы, боеспособны и не заняты другим боем,
дневные лимиты (5 на пару, 20 в сутки, BATTLE_ENGINE.md 1.2/4.4), у обоих открыта
личка с ботом (без неё некуда доставить секретный выбор "всерьёз/фора").

Дуэль из лички инициатора (соперник через @username): сопернику эта личка не видна,
поэтому приглашение уходит в обе лички (is_private_origin у DuelSession).

Цель — ответом или @username/id: по CLAUDE.md это два хендлера. Как у прода, команда
ловится по началу текста: "дуэльный" тоже её запускает и получает подсказку или
"Пользователь не найден", а цель — весь остаток текста после первого слова.
"""

import logging
from typing import Any

from selfrot import MessageHandler
from selfrot.exceptions import TelegramAPIError
from selfrot.filter import HasReplyUser, HasUser, TextStartswith

from src.bot.exceptions import (
    FighterHasPendingBattleError,
    FighterIsDeadError,
    FighterNotCombatReadyError,
)
from src.bot.game_configs import DUEL_CONFIG

from ....context import AppContext
from ....services.lookup import find_user
from ....types import TextUserMessage, TextUserReplyMessage
from .keyboards import consent_keyboard

logger = logging.getLogger(__name__)

_COMMAND = TextStartswith("дуэль", ignore_case=True) & HasUser()


class DuelInvite:
    """Общая часть обоих хендлеров: всё после того, как соперник найден. Как и
    миксины targeting.py, не наследует MessageHandler: его каждый хендлер пишет
    вторым базовым классом сам."""

    ctx: AppContext[Any]

    async def invite(self, target_id: int) -> None:
        ctx = self.ctx
        message = ctx.message
        initiator_id: int = message.user.id
        battles = ctx.battle_record_service

        if target_id == initiator_id:
            await message.reply("Нельзя вызвать на дуэль самого себя.")
            return

        initiator_user = await ctx.user_service.get(find_by=initiator_id)
        target_user = await ctx.user_service.get(find_by=target_id)
        if not initiator_user or not target_user:
            await message.reply("Один из участников не зарегистрирован.")
            return

        if not initiator_user.has_private_chat or not target_user.has_private_chat:
            who = "Тебе" if not initiator_user.has_private_chat else "Сопернику"
            await message.reply(
                f"{who} нужно один раз написать боту в ЛС (подойдёт /start) - иначе "
                f"часть сообщений о бое некуда будет доставить."
            )
            return

        initiator_ghoul = await ctx.ghoul_service.get(initiator_id)
        target_ghoul = await ctx.ghoul_service.get(target_id)
        if not initiator_ghoul:
            await message.reply("У тебя ещё нет гуля.")
            return
        if not target_ghoul:
            await message.reply("У соперника ещё нет гуля.")
            return

        try:
            await ctx.battle_service.validate_duel(
                initiator_ghoul,
                target_ghoul,
                has_pending_confirmation=lambda g: battles.is_busy(g.telegram_id),
            )
        except FighterIsDeadError:
            await message.reply("Один из участников мёртв.")
            return
        except FighterNotCombatReadyError as exc:
            await message.reply(
                f"Один из участников небоеспособен: {exc.health} HP "
                f"(нужно минимум {exc.threshold})."
            )
            return
        except FighterHasPendingBattleError:
            await message.reply("Один из участников уже занят другим боем.")
            return

        per_pair = DUEL_CONFIG.max_battles_per_day_pair
        per_day = DUEL_CONFIG.max_battles_per_day_total
        if await battles.count_pair_last_24h(initiator_id, target_id) >= per_pair:
            await message.reply(
                f"Лимит боёв с этим соперником на сегодня исчерпан ({per_pair}/сутки)."
            )
            return
        if await battles.count_total_last_24h(initiator_id) >= per_day:
            await message.reply(f"Твой дневной лимит боёв исчерпан ({per_day}/сутки).")
            return
        if await battles.count_total_last_24h(target_id) >= per_day:
            await message.reply("У соперника исчерпан дневной лимит боёв на сегодня.")
            return

        if not await battles.try_claim_duel(initiator_id, target_id):
            await message.reply(
                "Не удалось начать дуэль - один из участников уже занят."
            )
            return

        is_private_origin = message.chat.type == "private"
        duel_session = await ctx.duel_service.create(
            chat_id=message.chat.id,
            initiator_telegram_id=initiator_id,
            target_telegram_id=target_id,
            is_private_origin=is_private_origin,
        )

        # full_name БД-пользователя без фамилии кончается пробелом: как у прода.
        invite_text = (
            f"⚔️ {initiator_user.full_name} вызывает {target_user.full_name} на дуэль!\n"
            f"Бой начнётся только после подтверждения ОБЕИХ сторон."
        )
        keyboard = consent_keyboard(duel_session.id, initiator_id, target_id)

        if not is_private_origin:
            sent = await message.answer(invite_text, reply_markup=keyboard)
            await ctx.duel_service.atomic_update(
                duel_session.id, "awaiting_consent", consent_message_id=sent.message_id
            )
            return

        # Лички инициатора и соперника друг другу не видны: приглашение в обе.
        # id сообщений не запоминаются, дальше их не редактируем.
        for chat_id in (initiator_id, target_id):
            try:
                await ctx.bot.send_message(
                    chat_id=chat_id, text=invite_text, reply_markup=keyboard
                )
            except TelegramAPIError:
                logger.warning(
                    "duel %s: failed to deliver invite to %s", duel_session.id, chat_id
                )


class DuelRepliedHandler(DuelInvite, MessageHandler[AppContext[TextUserReplyMessage]]):
    query = _COMMAND & HasReplyUser()

    async def handle(self) -> None:
        await self.invite(self.ctx.message.reply_to_message.user.id)


class DuelHandler(DuelInvite, MessageHandler[AppContext[TextUserMessage]]):
    query = _COMMAND & ~HasReplyUser()

    usage = (
        "Вызови реплаем на сообщение соперника, либо «дуэль @username» / «дуэль <id>»."
    )

    async def handle(self) -> None:
        message = self.ctx.message

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(self.usage)
            return

        query = args[1].strip()
        target = await find_user(self.ctx.user_service, query)
        if target is None:
            await message.reply(f"Пользователь не найден: {query}")
            return

        await self.invite(target.telegram_id)
