import time

from selfrot.types import ChatMember, ChatMemberAdministrator, ChatMemberOwner

from src.bot.dialogs import Line
from src.bot.exceptions import (
    BotLacksRight,
    TargetAbsent,
    TargetIsAdmin,
    TargetNotBanned,
    TargetNotMuted,
)
from src.bot.types import ChatRight

from ..flow import ModerationFlow, has_right


class PunishmentFlow(ModerationFlow):
    right = ChatRight.RESTRICT_MEMBERS

    def not_found(self, target: str) -> Line:
        return self.phrases.user_not_found(query=target)

    async def check_rights(self) -> int:
        moderator_id = await self.check_moderator()

        # Чужих ботов Telegram в списке админов не отдаёт: бот в нём — это мы.
        administrators = await self.ctx.chat_administrators()
        bot = next((a for a in administrators if a.user.is_bot), None)
        if not has_right(bot, self.right):
            raise BotLacksRight(self.right)

        return moderator_id

    async def target_member(self, telegram_id: int) -> ChatMember:
        return await self.ctx.bot.get_chat_member(self.ctx.message.chat.id, telegram_id)

    async def punishable(self, telegram_id: int) -> ChatMember:
        member = await self.target_member(telegram_id)
        if isinstance(member, (ChatMemberOwner, ChatMemberAdministrator)):
            raise TargetIsAdmin(member.user.first_name)
        return member

    def until_date(self, seconds: int | None) -> int | None:
        return None if seconds is None else int(time.time()) + seconds

    async def on_error(self, exc: Exception) -> None:
        phrases = self.phrases
        match exc:
            case TargetIsAdmin(name=name):
                line = phrases.target_is_admin(name=name)
            case TargetNotMuted(name=name):
                line = phrases.not_muted(name=name)
            case TargetNotBanned(name=name):
                line = phrases.not_banned(name=name)
            case TargetAbsent(name=name):
                line = phrases.target_absent(name=name)
            case _:
                await super().on_error(exc)
                return
        await self.ctx.say(line, reply=True)
