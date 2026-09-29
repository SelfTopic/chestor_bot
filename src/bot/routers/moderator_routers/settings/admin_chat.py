from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.exceptions import TelegramAPIError
from selfrot.filter import HasUser
from selfrot.types import ChatFullInfo, ChatMemberAdministrator, ChatMemberOwner

from src.bot.exceptions import (
    AdminChatIsSelf,
    AdminChatNotFound,
    AdminChatNotLinked,
    AdminChatTaken,
    AnonymousModerator,
    NotChatOwner,
)

from ....context import AppContext
from ...types import TextUserMessage
from ..filters import InGroup, is_anonymous_admin
from ..flow import ModerationFlow, command

UNLINK_WORDS = ("off", "отвязать")


class AdminChatArgs(CommandArgs):
    chat: Rest = ""


class AdminChatHandler(ModerationFlow, MessageHandler[AppContext[TextUserMessage]]):
    cmd = command("set_admin_chat", "чат админов", AdminChatArgs)
    query = cmd & HasUser() & InGroup()

    async def handle(self) -> None:
        arg = self.cmd.parse(self.ctx).chat
        if not arg:
            await self.show()
        elif arg.lower() in UNLINK_WORDS:
            await self.unlink()
        else:
            target = await self.resolve(arg)
            if target is not None:
                await self.link(target)

    async def resolve(self, text: str) -> ChatFullInfo | None:
        reference = int(text) if text.lstrip("-").isdigit() else "@" + text.lstrip("@")
        try:
            chat = await self.ctx.bot.get_chat(reference)
        except TelegramAPIError:
            chat = None

        if chat is None or chat.type not in ("group", "supergroup"):
            # Обычному участнику — тишина, даже если чат не нашёлся.
            if await self.sender_is_admin():
                raise AdminChatNotFound(text)
            return None
        return chat

    async def show(self) -> None:
        if not await self.sender_is_admin():
            return

        if self.admin_chat_id is None:
            await self.ctx.say(self.phrases.admin_chat_none(), reply=True)
            return

        title = await self.title_of(self.admin_chat_id)
        await self.ctx.say(self.phrases.admin_chat_current(chat=title), reply=True)

    async def link(self, target: ChatFullInfo) -> None:
        here = self.ctx.message.chat.id
        if await self.ctx.moderation_service.admin_chat_requested(target.id, here):
            await self.confirm(target)
        else:
            await self.request(target)

    async def request(self, admin_chat: ChatFullInfo) -> None:
        if not await self.owns_this_chat():
            return

        chat = self.ctx.message.chat
        await self.ctx.moderation_service.request_admin_chat(chat.id, admin_chat.id)
        reference = f"@{chat.username}" if chat.username else str(chat.id)
        requested = self.phrases.admin_chat_requested(
            chat=admin_chat.title or str(admin_chat.id),
            command=f"/set_admin_chat {reference}",
        )
        await self.ctx.say(requested, reply=True)

    async def confirm(self, moderated: ChatFullInfo) -> None:
        message = self.ctx.message
        if is_anonymous_admin(message):
            raise AnonymousModerator()

        settings = await self.ctx.moderation_service.settings(moderated.id)
        self.voice = settings.voice
        member = await self.ctx.bot.get_chat_member(moderated.id, message.user.id)
        if not isinstance(member, ChatMemberOwner):
            if (
                isinstance(member, ChatMemberAdministrator)
                or await self.sender_is_admin()
            ):
                raise NotChatOwner()
            return

        previous = await self.ctx.moderation_service.link_admin_chat(
            moderated.id, message.chat.id
        )
        title = moderated.title or str(moderated.id)
        await self.ctx.say(self.phrases.admin_chat_linked(chat=title), reply=True)
        if previous is not None:
            unlinked = self.phrases.log_unlinked(
                chat=title, moderator=self.moderator_name
            )
            self.report(unlinked, previous)

    async def unlink(self) -> None:
        if not await self.owns_this_chat():
            return

        previous = await self.ctx.moderation_service.unlink_admin_chat(
            self.ctx.message.chat.id
        )
        title = await self.title_of(previous)
        await self.ctx.say(self.phrases.admin_chat_unlinked(chat=title), reply=True)
        unlinked = self.phrases.log_unlinked(
            chat=self.chat_title, moderator=self.moderator_name
        )
        self.report(unlinked, previous)

    async def title_of(self, chat_id: int) -> str:
        try:
            chat = await self.ctx.bot.get_chat(chat_id)
        except TelegramAPIError:
            return str(chat_id)
        return chat.title or str(chat_id)

    async def sender_is_admin(self) -> bool:
        message = self.ctx.message
        if is_anonymous_admin(message):
            return True
        administrators = await self.ctx.chat_administrators()
        return any(a.user.id == message.user.id for a in administrators)

    async def owns_this_chat(self) -> bool:
        message = self.ctx.message
        if is_anonymous_admin(message):
            raise AnonymousModerator()

        administrators = await self.ctx.chat_administrators()
        member = next((a for a in administrators if a.user.id == message.user.id), None)
        if member is None:
            return False
        if not isinstance(member, ChatMemberOwner):
            raise NotChatOwner()
        return True

    async def on_error(self, exc: Exception) -> None:
        phrases = self.phrases
        match exc:
            case NotChatOwner():
                line = phrases.owner_only()
            case AdminChatNotFound(query=query):
                line = phrases.admin_chat_not_found(query=query)
            case AdminChatIsSelf():
                line = phrases.admin_chat_self()
            case AdminChatTaken():
                line = phrases.admin_chat_taken()
            case AdminChatNotLinked():
                line = phrases.admin_chat_not_linked()
            case _:
                await super().on_error(exc)
                return
        await self.ctx.say(line, reply=True)
