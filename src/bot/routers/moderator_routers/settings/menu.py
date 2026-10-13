import logging
from collections.abc import Callable
from typing import Any

from selfrot import MessageHandler
from selfrot.exceptions import TelegramAPIError, TelegramNetworkError
from selfrot.filter import AnyCommand, Command, HasMessageCallbackQuery, HasUser
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import Message

from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import ChatNotFoundInDatabase
from src.bot.services.moderation import MAX_WARN_LIMIT, MIN_WARN_LIMIT
from src.bot.types import ChatModeration, ChatRight, ModerationFeature, ModerationVoice

from ....context import AppContext
from ...types import DataMessageCallbackQuery, TextUserMessage
from ..filters import FromChatAdmin
from ..flow import ModerationFlow, expiry_text, feature_name, has_right, right_name, term_text
from .menu_view import (
    MENU,
    MenuPress,
    MenuView,
    TermKey,
    next_penalty,
    shift_term,
    switch_text,
    term_key,
    term_seconds,
)
from .warns import penalty_text

logger = logging.getLogger(__name__)

# Запись в чат админов собирается уже новым голосом чата: голос мог смениться этим же нажатием.
LogLine = Callable[[Any], Line]


async def menu_view(ctx: AppContext[Any], chat_id: int, chat_title: str) -> MenuView:
    settings = await ctx.moderation_service.settings(chat_id)
    admin_title = None
    if settings.admin_chat_id is not None:
        try:
            admin_chat = await ctx.chat_service.get_by_telegram_id(settings.admin_chat_id)
        except ChatNotFoundInDatabase:
            admin_chat = None
        admin_title = (admin_chat.title if admin_chat else None) or str(settings.admin_chat_id)
    return MenuView(ctx, settings, chat_title, admin_title)


class ModerationMenuHandler(ModerationFlow, MessageHandler[AppContext[TextUserMessage]]):
    right = ChatRight.CHANGE_INFO
    cmd = AnyCommand(
        Command("moderation", args_count=0, ignore_case=True),
        Command("настройки модерации", args_count=0, prefixes="", ignore_case=True),
    )
    query = cmd & HasUser() & FromChatAdmin()

    def voiced_usage(self) -> Line:
        return MENU.hint()

    async def handle(self) -> None:
        message = self.ctx.message
        view = await menu_view(self.ctx, message.chat.id, self.chat_title)
        keyboard = view.keyboard()
        try:
            await message.reply_rich_message(rich_message=view.rich(), reply_markup=keyboard)
        except TelegramAPIError:
            logger.warning("Меню модерации не ушло rich-сообщением", exc_info=True)
            await message.reply(view.text(), reply_markup=keyboard)


class ModerationMenuPressHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    press = MenuPress.filter()
    query = press & HasMessageCallbackQuery()

    async def handle(self) -> None:
        ctx = self.ctx
        callback = ctx.callback_query
        message = callback.message
        if not isinstance(message, Message):
            await callback.answer(ctx.text(Dialogs.errors.cannot_process()))
            return

        payload = self.press.parse(ctx)
        if payload.action == "noop":
            await callback.answer(ctx.text(MENU.use_arrows()))
            return

        administrators = await ctx.chat_administrators()
        member = next((a for a in administrators if a.user.id == callback.user.id), None)
        if member is None:
            await callback.answer(ctx.text(MENU.not_admin()), show_alert=True)
            return
        if not has_right(member, ChatRight.CHANGE_INFO):
            right = ctx.text(right_name(ChatRight.CHANGE_INFO))
            await callback.answer(ctx.text(MENU.no_right(right=right)), show_alert=True)
            return

        chat_id = message.chat.id
        settings = await ctx.moderation_service.settings(chat_id)
        log = await self.apply(settings, payload)
        if log is None:
            await callback.answer(ctx.text(MENU.saved()))
            return

        chat_title = message.chat.title or str(chat_id)
        view = await menu_view(ctx, chat_id, chat_title)
        try:
            await message.edit_text(rich_message=view.rich(), reply_markup=view.keyboard())
        except TelegramAPIError:
            await message.edit_text(view.text(), reply_markup=view.keyboard())
        await callback.answer(ctx.text(MENU.saved()))
        await self.report(view.settings, log(self.phrases(view.settings)), chat_title)

    def phrases(self, settings: ChatModeration) -> Any:
        if settings.voice is ModerationVoice.ROUGH:
            return Dialogs.moderation.rough
        return Dialogs.moderation.neutral

    async def report(self, settings: ChatModeration, line: Line, chat_title: str) -> None:
        if settings.admin_chat_id is None:
            return
        try:
            await self.ctx.bot.send_message(settings.admin_chat_id, self.ctx.text(line))
        except (TelegramAPIError, TelegramNetworkError):
            logger.warning("Чат админов %s не получил запись модерации", settings.admin_chat_id)

    async def apply(self, settings: ChatModeration, payload: MenuPress) -> LogLine | None:
        ctx = self.ctx
        service = ctx.moderation_service
        chat_id = settings.chat_id
        callback = ctx.callback_query
        message = callback.message
        chat = (message.chat.title if isinstance(message, Message) else None) or str(chat_id)
        who = dict(chat=chat, moderator=callback.user.first_name)

        match payload.action:
            case "toggle":
                feature = ModerationFeature(payload.key)
                enabled = not settings.enabled(feature)
                await service.set_feature(chat_id, feature, enabled)
                name = ctx.text(feature_name(feature))
                state = switch_text(ctx, enabled)
                return lambda p: p.log_feature(feature=name, state=state, **who)
            case "term":
                key = term_key(payload.key)
                if key is None:
                    return None
                seconds = shift_term(term_seconds(settings, key), payload.step)
                return await self.store_term(settings, key, seconds, who)
            case "limit":
                limit = min(MAX_WARN_LIMIT, max(MIN_WARN_LIMIT, settings.warn_limit + payload.step))
                if limit == settings.warn_limit:
                    return None
                await service.set_warn_limit(chat_id, limit)
                return lambda p: p.log_warn_limit(limit=limit, **who)
            case "penalty":
                penalty = next_penalty(settings.warn_penalty)
                await service.set_warn_penalty(chat_id, penalty, settings.warn_penalty_seconds)
                text = penalty_text(ctx, penalty, settings.warn_penalty_seconds)
                return lambda p: p.log_warn_penalty(penalty=text, **who)
            case "voice":
                voice = (
                    ModerationVoice.NEUTRAL
                    if settings.voice is ModerationVoice.ROUGH
                    else ModerationVoice.ROUGH
                )
                await service.set_voice(chat_id, voice)
                return lambda p: p.log_voice(**who)
            case _:
                return None

    async def store_term(
        self, settings: ChatModeration, key: TermKey, seconds: int | None, who: dict[str, str]
    ) -> LogLine:
        ctx = self.ctx
        service = ctx.moderation_service
        chat_id = settings.chat_id
        match key:
            case "mute":
                await service.set_mute_default(chat_id, seconds)
                term = term_text(ctx, seconds)
                return lambda p: p.log_mute_default(term=term, **who)
            case "ban":
                await service.set_ban_default(chat_id, seconds)
                term = term_text(ctx, seconds)
                return lambda p: p.log_ban_default(term=term, **who)
            case "penalty":
                await service.set_warn_penalty(chat_id, settings.warn_penalty, seconds)
                text = penalty_text(ctx, settings.warn_penalty, seconds)
                return lambda p: p.log_warn_penalty(penalty=text, **who)
            case "expiry":
                await service.set_warn_expiry(chat_id, seconds)
                term = expiry_text(ctx, seconds)
                return lambda p: p.log_warn_expiry(term=term, **who)
