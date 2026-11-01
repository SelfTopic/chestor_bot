from datetime import datetime, timezone
from typing import Any, ClassVar

from selfrot import CommandArgs, MessageHandler, Pagination, Rest, ViewContent
from selfrot.context import BaseContext
from selfrot.filter import HasMessageCallbackQuery, HasUser
from selfrot.handlers import CallbackQueryHandler

from src.bot.dialogs import Dialogs, Line
from src.bot.repositories import ListedPunishment
from src.bot.types import ChatRight, ModerationActionType

from ....context import AppContext
from ...types import DataMessageCallbackQuery, TextUserMessage
from ..filters import FromChatAdmin
from ..flow import ModerationFlow, command, duration_text, has_right

PHRASES = Dialogs.moderation.lists


def app_context(ctx: BaseContext[Any]) -> AppContext[Any]:
    assert isinstance(ctx, AppContext)
    return ctx


# Секунды в списке — шум: до минуты точность не нужна.
def rough_duration(ctx: AppContext[Any], seconds: int) -> str:
    seconds = max(1, seconds)
    return duration_text(ctx, seconds - seconds % 60 if seconds >= 60 else seconds)


class PunishmentPages:
    kind: ClassVar[ModerationActionType]
    per_page = 10

    @classmethod
    def title(cls, count: int) -> Line:
        raise NotImplementedError

    @classmethod
    async def total(cls, ctx: BaseContext[Any]) -> int:
        app = app_context(ctx)
        chat = app.chat
        assert chat is not None
        return await app.moderation_service.count_listed(chat.id, cls.kind)

    @classmethod
    async def page_content(cls, ctx: BaseContext[Any], page: int) -> ViewContent:
        app = app_context(ctx)
        chat = app.chat
        assert chat is not None
        service = app.moderation_service
        total = await service.count_listed(chat.id, cls.kind)
        listed = await service.listed_page(chat.id, cls.kind, page, cls.per_page)
        first = page * cls.per_page + 1
        items = "\n".join(
            app.text(cls.item(app, place, punishment))
            for place, punishment in enumerate(listed, start=first)
        )
        title = app.text(cls.title(total))
        return ViewContent(body=app.text(PHRASES.page(title=title, items=items)))

    @classmethod
    def item(cls, ctx: AppContext[Any], place: int, punishment: ListedPunishment) -> Line:
        # Время в БД — UTC без зоны, как его пишет Postgres.
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        unknown = ctx.text(PHRASES.unknown())
        who = dict(
            place=place,
            name=punishment.target_name or str(punishment.target_id),
            moderator=punishment.moderator_name or unknown,
        )
        reason = punishment.reason
        if cls.kind is ModerationActionType.KICK:
            ago = rough_duration(ctx, int((now - punishment.created_at).total_seconds()))
            if reason is None:
                return PHRASES.kick_item(ago=ago, **who)
            return PHRASES.kick_item_for(ago=ago, reason=reason, **who)

        if punishment.expires_at is None:
            term = ctx.text(Dialogs.moderation.term.forever())
        else:
            seconds = int((punishment.expires_at - now).total_seconds())
            term = ctx.text(PHRASES.left(duration=rough_duration(ctx, seconds)))
        if reason is None:
            return PHRASES.item(term=term, **who)
        return PHRASES.item_for(term=term, reason=reason, **who)


class MuteList(PunishmentPages, Pagination, prefix="mutelist"):
    kind = ModerationActionType.MUTE

    @classmethod
    def title(cls, count: int) -> Line:
        return PHRASES.mute_title(count=count)


class BanList(PunishmentPages, Pagination, prefix="banlist"):
    kind = ModerationActionType.BAN

    @classmethod
    def title(cls, count: int) -> Line:
        return PHRASES.ban_title(count=count)


class WarnList(PunishmentPages, Pagination, prefix="warnlist"):
    kind = ModerationActionType.WARN

    @classmethod
    def title(cls, count: int) -> Line:
        return PHRASES.warn_title(count=count)


class KickList(PunishmentPages, Pagination, prefix="kicklist"):
    kind = ModerationActionType.KICK

    @classmethod
    def title(cls, count: int) -> Line:
        return PHRASES.kick_title(count=count)


class ListArgs(CommandArgs):
    rest: Rest = ""


class PunishmentListFlow(ModerationFlow):
    right = ChatRight.RESTRICT_MEMBERS
    pages: ClassVar[type[Pagination]]
    empty: ClassVar[Line]

    async def handle(self) -> None:
        await self.check_moderator()
        if await self.pages.total(self.ctx) == 0:
            await self.ctx.say(self.empty, reply=True)
            return
        await self.pages.show(self.ctx)


class MuteListHandler(PunishmentListFlow, MessageHandler[AppContext[TextUserMessage]]):
    cmd = command("mutelist", ("мутлист", "mutelist"), ListArgs)
    query = cmd & HasUser() & FromChatAdmin()
    pages = MuteList
    empty = PHRASES.mute_empty()


class BanListHandler(PunishmentListFlow, MessageHandler[AppContext[TextUserMessage]]):
    cmd = command("banlist", ("банлист", "banlist"), ListArgs)
    query = cmd & HasUser() & FromChatAdmin()
    pages = BanList
    empty = PHRASES.ban_empty()


class WarnListHandler(PunishmentListFlow, MessageHandler[AppContext[TextUserMessage]]):
    cmd = command("warnlist", ("варнлист", "warnlist"), ListArgs)
    query = cmd & HasUser() & FromChatAdmin()
    pages = WarnList
    empty = PHRASES.warn_empty()


class KickListHandler(PunishmentListFlow, MessageHandler[AppContext[TextUserMessage]]):
    cmd = command("kicklist", ("киклист", "kicklist"), ListArgs)
    query = cmd & HasUser() & FromChatAdmin()
    pages = KickList
    empty = PHRASES.kick_empty()


class PunishmentPagePress:
    ctx: AppContext[DataMessageCallbackQuery]
    pages: ClassVar[type[Pagination]]

    async def handle(self) -> None:
        query = self.ctx.callback_query
        administrators = await self.ctx.chat_administrators()
        moderator = next((a for a in administrators if a.user.id == query.user.id), None)
        if not has_right(moderator, ChatRight.RESTRICT_MEMBERS):
            await query.answer(self.ctx.text(PHRASES.only_moderators()), show_alert=True)
            return
        await self.pages.press(self.ctx)


class MuteListPressHandler(
    PunishmentPagePress, CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]
):
    query = MuteList.filter() & HasMessageCallbackQuery()
    pages = MuteList


class BanListPressHandler(
    PunishmentPagePress, CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]
):
    query = BanList.filter() & HasMessageCallbackQuery()
    pages = BanList


class WarnListPressHandler(
    PunishmentPagePress, CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]
):
    query = WarnList.filter() & HasMessageCallbackQuery()
    pages = WarnList


class KickListPressHandler(
    PunishmentPagePress, CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]
):
    query = KickList.filter() & HasMessageCallbackQuery()
    pages = KickList
