from selfrot import BaseRouter, Bot, CallbackPayload, InlineKeyboard, button
from selfrot.exceptions import TelegramAPIError
from selfrot.filter import HasMessageCallbackQuery
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import Message

from src.bot.dialogs import Dialogs
from src.bot.game_configs import CULT_CONFIG
from src.bot.session_services import SessionServices
from src.bot.utils import format_amount, utcnow_naive

from ...context import AppContext
from ..types import DataMessageCallbackQuery


class CultMutePress(CallbackPayload, prefix="cult_mute"):
    pass


# Деньги начисляются в одной транзакции, а сообщения — после коммита: недошедшее
# уведомление не отменяет выплату.
async def reward_cult_hashtags(services: SessionServices, bot: Bot) -> None:
    payouts = await services.cult_service.pay_due(utcnow_naive())
    await services.session.commit()

    reward = Dialogs.cult.reward(amount=format_amount(CULT_CONFIG.reward))
    for payout in payouts:
        if not payout.notify:
            continue
        text = await services.language_service.text_for(payout.telegram_id)
        keyboard = InlineKeyboard().row(button(text(Dialogs.cult.mute_button()), CultMutePress()))
        try:
            await bot.send_message(
                chat_id=payout.telegram_id, text=text(reward), reply_markup=keyboard.markup()
            )
        except TelegramAPIError:
            pass


class CultMuteHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    query = CultMutePress.filter() & HasMessageCallbackQuery()

    async def handle(self) -> None:
        callback = self.ctx.callback_query
        await self.ctx.cult_service.mute(callback.user.id)
        if isinstance(callback.message, Message):
            await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer(self.ctx.text(Dialogs.cult.muted()), show_alert=True)


class CultRouter(BaseRouter[AppContext]):
    handlers = (CultMuteHandler,)
