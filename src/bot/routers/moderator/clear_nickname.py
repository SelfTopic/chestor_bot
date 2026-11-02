from selfrot import MessageHandler
from selfrot.filter import HasReplyUser, HasUser, Text

from src.bot.dialogs import Dialogs

from ...context import AppContext
from ..types import TextUserReplyMessage
from .filters import FromChatAdmin

PHRASES = Dialogs.nickname


class ClearMemberNicknameHandler(MessageHandler[AppContext[TextUserReplyMessage]]):
    query = (
        (Text("-ник", ignore_case=True) | Text("-nick", ignore_case=True))
        & HasUser()
        & HasReplyUser()
        & FromChatAdmin()
    )

    async def handle(self) -> None:
        ctx = self.ctx
        message = ctx.message
        target = message.reply_to_message.user
        nickname = await ctx.nickname_service.clear(message.chat.id, target.id)
        if nickname is None:
            await ctx.say(PHRASES.target_has_none(name=target.first_name), reply=True)
            return

        moderator = await ctx.moderated_name(message.user.id, message.user.first_name)
        line = PHRASES.cleared_by_moderator(
            moderator=moderator, name=target.first_name, nickname=nickname
        )
        await ctx.say(line)
