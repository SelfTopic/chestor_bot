import logging
from collections.abc import Callable
from typing import Any

from selfrot import CallbackPayload, MessageHandler, View, ViewContent
from selfrot.context import BaseContext
from selfrot.exceptions import TelegramAPIError, TelegramNetworkError
from selfrot.filter import AnyCommand, Command, HasMessageCallbackQuery, HasUser
from selfrot.handlers import CallbackQueryHandler

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
    MenuTable,
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


def app_context(ctx: BaseContext[Any]) -> AppContext[Any]:
    assert isinstance(ctx, AppContext)
    return ctx


class ModerationMenu(View):
    payload = MenuPress

    @classmethod
    async def render(cls, ctx: BaseContext[Any], data: CallbackPayload | None) -> ViewContent:
        app = app_context(ctx)
        chat_id = app.chat_id
        settings = await app.moderation_service.settings(chat_id)
        table = MenuTable(app, settings, cls.chat_title(app), await cls.admin_title(app, settings))
        return ViewContent(body=table.rich(), rows=table.buttons())

    @classmethod
    def chat_title(cls, ctx: AppContext[Any]) -> str:
        chat = ctx.chat
        assert chat is not None
        return chat.title or str(chat.id)

    @classmethod
    async def admin_title(cls, ctx: AppContext[Any], settings: ChatModeration) -> str | None:
        if settings.admin_chat_id is None:
            return None
        try:
            admin_chat = await ctx.chat_service.get_by_telegram_id(settings.admin_chat_id)
        except ChatNotFoundInDatabase:
            admin_chat = None
        return (admin_chat.title if admin_chat else None) or str(settings.admin_chat_id)

    @classmethod
    async def apply(cls, ctx: BaseContext[Any], data: CallbackPayload) -> None:
        app = app_context(ctx)
        assert isinstance(data, MenuPress)
        settings = await app.moderation_service.settings(app.chat_id)
        log = await cls.change(app, settings, data)
        if log is None:
            return

        changed = await app.moderation_service.settings(app.chat_id)
        await cls.report(app, changed, log(cls.phrases(changed)))

    @classmethod
    def phrases(cls, settings: ChatModeration) -> Any:
        if settings.voice is ModerationVoice.ROUGH:
            return Dialogs.moderation.rough
        return Dialogs.moderation.neutral

    @classmethod
    async def report(cls, ctx: AppContext[Any], settings: ChatModeration, line: Line) -> None:
        if settings.admin_chat_id is None:
            return
        try:
            await ctx.bot.send_message(settings.admin_chat_id, ctx.text(line))
        except (TelegramAPIError, TelegramNetworkError):
            logger.warning("Чат админов %s не получил запись модерации", settings.admin_chat_id)

    @classmethod
    async def change(
        cls, ctx: AppContext[Any], settings: ChatModeration, payload: MenuPress
    ) -> LogLine | None:
        service = ctx.moderation_service
        chat_id = settings.chat_id
        who = dict(chat=cls.chat_title(ctx), moderator=ctx.callback_query.user.first_name)

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
                return await cls.store_term(ctx, settings, key, seconds, who)
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

    @classmethod
    async def store_term(
        cls,
        ctx: AppContext[Any],
        settings: ChatModeration,
        key: TermKey,
        seconds: int | None,
        who: dict[str, str],
    ) -> LogLine:
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


class ModerationMenuHandler(ModerationFlow, MessageHandler[AppContext[TextUserMessage]]):
    right = ChatRight.CHANGE_INFO
    cmd = AnyCommand(
        Command("moderation", args_count=0, ignore_case=True),
        Command("настройки модерации", args_count=0, prefixes="", ignore_case=True),
        Command("moderation settings", args_count=0, prefixes="", ignore_case=True),
    )
    query = cmd & HasUser() & FromChatAdmin()

    def voiced_usage(self) -> Line:
        return MENU.hint()

    async def handle(self) -> None:
        await ModerationMenu.show(self.ctx)


# Подпись посередине ряда ничего не меняет: перерисовка без изменений — ошибка Telegram.
class ModerationMenuLabelHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    press = MenuPress.filter(action="noop")
    query = press & HasMessageCallbackQuery()

    async def handle(self) -> None:
        if self.press.parse(self.ctx).key == "edge":
            await self.ctx.callback_query.answer()
            return
        await self.ctx.callback_query.answer(self.ctx.text(MENU.use_arrows()))


class ModerationMenuPressHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    query = ModerationMenu.filter() & HasMessageCallbackQuery()

    async def handle(self) -> None:
        ctx = self.ctx
        callback = ctx.callback_query
        administrators = await ctx.chat_administrators()
        member = next((a for a in administrators if a.user.id == callback.user.id), None)
        if member is None:
            await callback.answer(ctx.text(MENU.not_admin()), show_alert=True)
            return
        if not has_right(member, ChatRight.CHANGE_INFO):
            right = ctx.text(right_name(ChatRight.CHANGE_INFO))
            await callback.answer(ctx.text(MENU.no_right(right=right)), show_alert=True)
            return

        await ModerationMenu.press(ctx)
