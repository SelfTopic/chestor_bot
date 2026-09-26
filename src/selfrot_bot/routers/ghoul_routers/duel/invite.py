"""
Шаг 1, "дуэль": приглашение с двумя кнопками (для инициатора и для соперника: сама
команда ещё не согласие). Таймаут согласия ведёт DuelTicker.

Проверки перед приглашением (оба живы, боеспособны, не заняты, дневные лимиты, у
обоих открыта личка с ботом) делает BattleService.open_duel; здесь только тексты
отказов и доставка приглашения. Дуэль из лички инициатора (соперник через
@username): сопернику эта личка не видна, поэтому приглашение уходит в обе лички
(is_private_origin у DuelSession).

Цель — ответом или @username/id: по CLAUDE.md это два хендлера на миксинах
targeting.py. Как у прода, цель — весь остаток текста после команды, а ошибки
приходят реплаем.

Исправленный прод-баг: прод ловил команду по началу текста, поэтому на "дуэльный
вызов" в чате бот отвечал "Пользователь не найден: вызов". Здесь это команда
"дуэль" целым словом (Command с prefixes="").
"""

import logging
from typing import Any

from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.exceptions import TelegramAPIError
from selfrot.filter import Command, HasReplyUser, HasUser

from src.bot.game_configs import DUEL_CONFIG

from ....context import AppContext
from ....services.battle import DuelRefusal, DuelRefused
from ...targeting import ExplicitTargetHandler, RepliedTargetHandler, TargetArgs
from ...types import TextUserMessage, TextUserReplyMessage
from .keyboards import consent_keyboard

logger = logging.getLogger(__name__)

_NO_PRIVATE_CHAT = (
    "{who} нужно один раз написать боту в ЛС (подойдёт /start) - иначе "
    "часть сообщений о бое некуда будет доставить."
)


class DuelInvite:
    """Общая часть обоих хендлеров: соперник уже известен. Как и миксины
    targeting.py, не наследует MessageHandler: его каждый хендлер пишет сам."""

    ctx: AppContext[Any]

    refusals = {
        DuelRefusal.SELF: "Нельзя вызвать на дуэль самого себя.",
        DuelRefusal.NOT_REGISTERED: "Один из участников не зарегистрирован.",
        DuelRefusal.INITIATOR_NO_PRIVATE_CHAT: _NO_PRIVATE_CHAT.format(who="Тебе"),
        DuelRefusal.TARGET_NO_PRIVATE_CHAT: _NO_PRIVATE_CHAT.format(who="Сопернику"),
        DuelRefusal.INITIATOR_NO_GHOUL: "У тебя ещё нет гуля.",
        DuelRefusal.TARGET_NO_GHOUL: "У соперника ещё нет гуля.",
        DuelRefusal.DEAD: "Один из участников мёртв.",
        DuelRefusal.NOT_COMBAT_READY: (
            "Один из участников небоеспособен: {health} HP (нужно минимум {threshold})."
        ),
        DuelRefusal.BUSY: "Один из участников уже занят другим боем.",
        DuelRefusal.PAIR_LIMIT: (
            "Лимит боёв с этим соперником на сегодня исчерпан ({per_pair}/сутки)."
        ),
        DuelRefusal.INITIATOR_DAY_LIMIT: "Твой дневной лимит боёв исчерпан ({per_day}/сутки).",
        DuelRefusal.TARGET_DAY_LIMIT: "У соперника исчерпан дневной лимит боёв на сегодня.",
        DuelRefusal.CLAIM_FAILED: "Не удалось начать дуэль - один из участников уже занят.",
    }

    def refusal_text(self, refused: DuelRefused) -> str:
        return self.refusals[refused.reason].format(
            health=refused.health,
            threshold=refused.threshold,
            per_pair=DUEL_CONFIG.max_battles_per_day_pair,
            per_day=DUEL_CONFIG.max_battles_per_day_total,
        )

    async def perform(self, telegram_id: int, args: Any) -> None:
        ctx = self.ctx
        message = ctx.message
        private = message.chat.type == "private"

        try:
            duel = await ctx.battle_service.open_duel(
                message.user.id, telegram_id, chat_id=message.chat.id, private=private
            )
        except DuelRefused as refused:
            await message.reply(self.refusal_text(refused))
            return

        session = duel.session
        # full_name БД-пользователя без фамилии кончается пробелом: как у прода.
        text = (
            f"⚔️ {duel.initiator_name} вызывает {duel.target_name} на дуэль!\n"
            f"Бой начнётся только после подтверждения ОБЕИХ сторон."
        )
        keyboard = consent_keyboard(
            session.id, session.initiator_telegram_id, session.target_telegram_id
        )

        if not private:
            sent = await message.answer(text, reply_markup=keyboard)
            await ctx.duel_service.atomic_update(
                session.id, "awaiting_consent", consent_message_id=sent.message_id
            )
            return

        # Лички инициатора и соперника друг другу не видны: приглашение в обе.
        # id сообщений не запоминаются, дальше их не редактируем.
        for chat_id in (session.initiator_telegram_id, session.target_telegram_id):
            try:
                await ctx.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
            except TelegramAPIError:
                logger.warning("duel %s: failed to deliver invite to %s", session.id, chat_id)


class DuelRepliedArgs(CommandArgs):
    note: Rest = ""  # текст после "дуэль" в ответе на сообщение не нужен, как у прода


class DuelRepliedHandler(
    DuelInvite,
    RepliedTargetHandler[DuelRepliedArgs],
    MessageHandler[AppContext[TextUserReplyMessage]],
):
    cmd = Command("дуэль", DuelRepliedArgs, prefixes="", ignore_case=True)
    query = cmd & HasUser() & HasReplyUser()


class DuelArgs(TargetArgs):
    target: Rest  # весь остаток: "дуэль @a b" ищет "@a b", как у прода


class DuelHandler(
    DuelInvite,
    ExplicitTargetHandler[DuelArgs],
    MessageHandler[AppContext[TextUserMessage]],
):
    cmd = Command("дуэль", DuelArgs, prefixes="", ignore_case=True)
    query = cmd & HasUser() & ~HasReplyUser()
    usage = "Вызови реплаем на сообщение соперника, либо «дуэль @username» / «дуэль <id>»."
    not_found_text = "Пользователь не найден: {target}"
    reply_errors = True
