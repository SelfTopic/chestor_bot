import logging

from selfrot import BaseMiddleware, BaseRouter, CallbackPayload, InlineKeyboard, button
from selfrot.exceptions import TelegramAPIError, TelegramNetworkError
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import (
    CallbackQuery,
    ChatMemberAdministrator,
    ChatMemberMember,
    ChatMemberOwner,
    ChatMemberRestricted,
    DataCallbackQuery,
    Message,
)

from src.bot.dialogs import Dialogs
from src.config import settings

from ...context import AppContext

logger = logging.getLogger(__name__)


class SubscriptionCheck(CallbackPayload, prefix="sub_check"):
    pass


async def subscribed(ctx: AppContext[object], telegram_id: int) -> bool:
    channel = settings.SUBSCRIPTION_CHANNEL
    cache = ctx.subscriber_cache
    if not channel or cache.is_fresh(telegram_id):
        return True

    try:
        member = await ctx.bot.get_chat_member(channel, telegram_id)
    # Бот не админ канала или Telegram не ответил: из-за этого игру не закрываем.
    except (TelegramAPIError, TelegramNetworkError) as exc:
        logger.warning("Subscription check for %s failed: %s", telegram_id, exc)
        return True

    if isinstance(member, (ChatMemberOwner, ChatMemberAdministrator, ChatMemberMember)) or (
        isinstance(member, ChatMemberRestricted) and member.is_member
    ):
        cache.confirm(telegram_id)
        return True
    return False


class ChannelSubscriptionMiddleware(BaseMiddleware[AppContext]):
    async def pre_handle(self) -> bool:
        user = self.ctx.user
        if user is None or await subscribed(self.ctx, user.id):
            return True

        channel = settings.SUBSCRIPTION_CHANNEL
        event = self.ctx.event
        if isinstance(event, CallbackQuery):
            alert = self.ctx.text(Dialogs.subscription.required_alert(channel=channel))
            await event.answer(alert, show_alert=True)
        elif isinstance(event, Message):
            link = f"https://t.me/{channel.lstrip('@')}"
            keyboard = (
                InlineKeyboard()
                .row(button(self.ctx.text(Dialogs.subscription.subscribe_button()), url=link))
                .row(button(self.ctx.text(Dialogs.subscription.check_button()), SubscriptionCheck()))
                .markup()
            )
            text = self.ctx.text(Dialogs.subscription.required(channel=channel))
            await event.answer(text, reply_markup=keyboard)
        return False

    async def post_handle(self, exc: BaseException | None = None) -> None:
        pass


class SubscriptionCheckHandler(CallbackQueryHandler[AppContext[DataCallbackQuery]]):
    query = SubscriptionCheck.filter()

    async def handle(self) -> None:
        callback = self.ctx.callback_query
        if await subscribed(self.ctx, callback.user.id):
            line = Dialogs.subscription.confirmed()
        else:
            line = Dialogs.subscription.not_yet()
        await callback.answer(self.ctx.text(line), show_alert=True)


class SubscriptionCheckRouter(BaseRouter[AppContext]):
    handlers = (SubscriptionCheckHandler,)
