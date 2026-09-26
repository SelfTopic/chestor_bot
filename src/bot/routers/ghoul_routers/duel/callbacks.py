"""
Шаги 2, 3 и 5: нажатия кнопок уже отправленной дуэли. Согласие обеих сторон, затем
(при перевесе >= DUEL_CONFIG.power_ratio_threshold) секретный выбор "всерьёз/фора"
в личке сильной стороны, затем бой (fight.run_and_announce_fight) и выбор победителя
"ограбить/отпустить/съесть" (fight.finalize_outcome). Таймауты шагов — DuelTicker.

Нажать можно только свою кнопку: у прода это проверка expected_id в хендлере, здесь
pressed_by("expected_id"), а чужое нажатие ловит следующий хендлер ("Это не твоя
кнопка."). Кнопка "duel:..." с испорченными данными, как у прода, получает пустой
ответ.
"""

import logging

from selfrot.exceptions import TelegramAPIError
from selfrot.filter import CallbackDataStartswith
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import DataCallbackQuery, Message

from ....context import AppContext
from .callback_data import DuelPress
from .fight import finalize_outcome, run_and_announce_fight
from .keyboards import consent_keyboard, fora_keyboard
from .services import DuelServices

logger = logging.getLogger(__name__)


class DuelPressHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    press = DuelPress.filter().pressed_by("expected_id")
    query = press

    async def handle(self) -> None:
        payload = self.press.parse(self.ctx)
        services = DuelServices.from_ctx(self.ctx)

        if payload.action in ("consent_initiator", "consent_target"):
            await self.consent(payload, services)
        elif payload.action in ("fora_serious", "fora_handicap"):
            await self.fora(payload, services)
        else:
            await self.outcome(payload, services)

    async def consent(self, payload: DuelPress, services: DuelServices) -> None:
        callback = self.ctx.callback_query
        bot = self.ctx.bot
        duel_id = payload.duel_id

        field = (
            "initiator_consented"
            if payload.action == "consent_initiator"
            else "target_consented"
        )
        updated = await services.duel_service.atomic_update(
            duel_id, "awaiting_consent", **{field: True}
        )
        if not updated:
            await callback.answer("Приглашение уже неактуально.", show_alert=True)
            return

        if not (updated.initiator_consented and updated.target_consented):
            await callback.answer("Принято, ждём второго участника.")
            if updated.consent_message_id:
                try:
                    await bot.edit_message_text(
                        chat_id=updated.chat_id,
                        message_id=updated.consent_message_id,
                        text="✅ Один из участников подтвердил, ждём второго.",
                        reply_markup=consent_keyboard(
                            duel_id,
                            updated.initiator_telegram_id,
                            updated.target_telegram_id,
                        ),
                    )
                except TelegramAPIError:
                    pass
            return

        await callback.answer("Оба подтвердили!")

        # Кнопки согласия больше не нужны: сообщение удаляется, а не правится.
        if updated.consent_message_id:
            try:
                await bot.delete_message(
                    chat_id=updated.chat_id, message_id=updated.consent_message_id
                )
            except TelegramAPIError:
                pass

        odds = await services.battle.duel_odds(updated)
        if odds is None:
            return

        if not odds.needs_fora_choice:
            session = await services.duel_service.atomic_update(
                duel_id, "awaiting_consent", stage="running", compress_hp=True
            )
            if session:
                await run_and_announce_fight(bot, session, services)
            return

        favored_id = odds.favored_telegram_id
        session = await services.duel_service.atomic_update(
            duel_id,
            "awaiting_consent",
            stage="awaiting_serious_or_handicap",
            favored_telegram_id=favored_id,
        )
        if not session:
            return

        if not updated.is_private_origin:
            try:
                await bot.send_message(
                    chat_id=updated.chat_id,
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

    async def fora(self, payload: DuelPress, services: DuelServices) -> None:
        callback = self.ctx.callback_query

        session = await services.duel_service.atomic_update(
            payload.duel_id,
            "awaiting_serious_or_handicap",
            stage="running",
            compress_hp=payload.action == "fora_handicap",
        )
        if not session:
            await callback.answer("Уже неактуально.", show_alert=True)
            return

        await callback.answer("Принято!")
        if isinstance(callback.message, Message):
            try:
                await callback.message.edit_text("Решение принято, бой начинается.")
            except TelegramAPIError:
                pass

        await run_and_announce_fight(self.ctx.bot, session, services)

    async def outcome(self, payload: DuelPress, services: DuelServices) -> None:
        callback = self.ctx.callback_query

        session = await services.duel_service.atomic_update(
            payload.duel_id,
            "awaiting_winner_choice",
            stage="done",
            winner_choice=payload.action,
        )
        if not session:
            await callback.answer("Уже неактуально.", show_alert=True)
            return

        await callback.answer("Принято!")
        await finalize_outcome(self.ctx.bot, session, payload.action, services)


class NotYourDuelButtonHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    query = DuelPress.filter()

    async def handle(self) -> None:
        await self.ctx.callback_query.answer("Это не твоя кнопка.", show_alert=True)


class MalformedDuelButtonHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    query = CallbackDataStartswith("duel:")

    async def handle(self) -> None:
        await self.ctx.callback_query.answer()
