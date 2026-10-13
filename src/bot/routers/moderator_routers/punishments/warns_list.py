from datetime import datetime, timezone

from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import AnyCommand, Command, HasReplyUser, HasUser

from src.bot.dialogs import Dialogs, Line
from src.bot.types import ChatRight
from src.database.models import ModerationWarning

from ....context import AppContext
from ...targeting import RepliedTargetHandler
from ...types import TextUserMessage, TextUserReplyMessage
from ..filters import FromChatAdmin, InGroup
from .targets import AnywhereTargetHandler, TargetTextArgs
from ..flow import ModerationFlow, command

LIST_WORDS = ("варны", "преды")


class WarnsListFlow(ModerationFlow):
    right = ChatRight.RESTRICT_MEMBERS

    def voiced_usage(self) -> Line:
        return self.phrases.warns_usage()

    def not_found(self, target: str) -> Line:
        return self.phrases.user_not_found(query=target)

    async def show(self, telegram_id: int, name: str) -> None:
        warnings = await self.ctx.moderation_service.warnings(
            self.ctx.message.chat.id, telegram_id
        )
        if not warnings:
            await self.ctx.say(self.phrases.warns_none(name=name), reply=True)
            return

        items = "\n".join(self.ctx.text(self.item(warning)) for warning in warnings)
        line = self.phrases.warns_list(
            name=name,
            count=len(warnings),
            limit=self.settings.warn_limit,
            items=items,
        )
        await self.ctx.say(line, reply=True)

    def item(self, warning: ModerationWarning) -> Line:
        reason = warning.reason or self.ctx.text(self.phrases.no_reason())
        if warning.expires_at is None:
            return self.phrases.warns_item_forever(reason=reason)

        # Время в БД — UTC без зоны, как его пишет Postgres.
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        seconds = max(1, int((warning.expires_at - now).total_seconds()))
        left = self.ctx.text(Dialogs.moderation.term.after(duration=self.duration(seconds)))
        return self.phrases.warns_item(reason=reason, left=left)

    async def show_member(self, telegram_id: int) -> None:
        member = await self.ctx.bot.get_chat_member(self.ctx.message.chat.id, telegram_id)
        await self.show(telegram_id, member.user.first_name)


class OwnWarnsHandler(WarnsListFlow, MessageHandler[AppContext[TextUserMessage]]):
    cmd = AnyCommand(
        Command("warns", args_count=0, ignore_case=True),
        *(Command(word, args_count=0, prefixes="", ignore_case=True) for word in LIST_WORDS),
    )
    query = cmd & HasUser() & ~HasReplyUser() & InGroup()

    async def handle(self) -> None:
        user = self.ctx.message.user
        await self.show(user.id, user.first_name)


class WarnsRepliedArgs(CommandArgs):
    note: Rest = ""


class WarnsRepliedHandler(
    WarnsListFlow,
    RepliedTargetHandler[WarnsRepliedArgs],
    MessageHandler[AppContext[TextUserReplyMessage]],
):
    cmd = command("warns", LIST_WORDS, WarnsRepliedArgs)
    query = cmd & HasUser() & HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, args: WarnsRepliedArgs) -> None:
        await self.show_member(telegram_id)


class WarnsHandler(
    WarnsListFlow,
    AnywhereTargetHandler,
    MessageHandler[AppContext[TextUserMessage]],
):
    cmd = command("warns", LIST_WORDS, TargetTextArgs)
    query = cmd & HasUser() & ~HasReplyUser() & FromChatAdmin()

    async def perform(self, telegram_id: int, rest: str) -> None:
        await self.show_member(telegram_id)
