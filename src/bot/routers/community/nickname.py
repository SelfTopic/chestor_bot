from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.filter import AnyCommand, Command, HasReplyUser, HasUser, Text

from src.bot.dialogs import Dialogs, Line
from src.bot.exceptions import NicknameProblem, NicknameRejected
from src.database.models import NICKNAME_MAX_LENGTH

from ...context import AppContext
from ..types import TextUserMessage, UserMessage

PHRASES = Dialogs.nickname


class NicknameArgs(CommandArgs):
    nickname: Rest = ""


class NicknameHandler(MessageHandler[AppContext[TextUserMessage]]):
    cmd = AnyCommand(
        Command("ник", NicknameArgs, prefixes="", ignore_case=True),
        Command("nick", NicknameArgs, prefixes="", ignore_case=True),
        Command("nick", NicknameArgs),
    )
    query = cmd & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        chat_id = ctx.nickname_chat
        if chat_id is None:
            await ctx.say(PHRASES.only_group(), reply=True)
            return

        raw = self.cmd.parse(ctx).nickname
        if not raw.strip():
            await ctx.say(self.current((await ctx.nicknames()).get(ctx.message.user.id)), reply=True)
            return

        try:
            nickname = await ctx.nickname_service.set(chat_id, ctx.message.user.id, raw)
        except NicknameRejected as rejected:
            await ctx.say(self.rejection(rejected.problem), reply=True)
            return
        await ctx.say(PHRASES.set(nickname=nickname), reply=True)

    def current(self, nickname: str | None) -> Line:
        if nickname is None:
            return PHRASES.none(limit=NICKNAME_MAX_LENGTH)
        return PHRASES.current(nickname=nickname)

    def rejection(self, problem: NicknameProblem) -> Line:
        match problem:
            case NicknameProblem.EMPTY:
                return PHRASES.none(limit=NICKNAME_MAX_LENGTH)
            case NicknameProblem.TOO_LONG:
                return PHRASES.too_long(limit=NICKNAME_MAX_LENGTH)
            case NicknameProblem.LINK:
                return PHRASES.link()


class ClearNicknameHandler(MessageHandler[AppContext[UserMessage]]):
    # Чужой ник реплаем снимает модератор: хендлер в routers/moderator.
    query = (Text("-ник", ignore_case=True) | Text("-nick", ignore_case=True)) & HasUser() & ~HasReplyUser()

    async def handle(self) -> None:
        ctx = self.ctx
        chat_id = ctx.nickname_chat
        if chat_id is None:
            await ctx.say(PHRASES.only_group(), reply=True)
            return

        user = ctx.message.user
        if await ctx.nickname_service.clear(chat_id, user.id) is None:
            await ctx.say(PHRASES.nothing_to_clear(), reply=True)
            return
        await ctx.say(PHRASES.cleared(name=user.first_name), reply=True)


class NicknameRouter(BaseRouter[AppContext]):
    handlers = (NicknameHandler, ClearNicknameHandler)
