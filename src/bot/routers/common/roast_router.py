from selfrot import BaseRouter, MessageHandler
from selfrot.filter import HasText, HasUser

from src.bot.dialogs import Dialogs
from src.bot.services.roast import Incoming

from ...context import AppContext
from ..types import TextUserMessage

GROUP_CHATS = ("group", "supergroup")


class RoastHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = HasText() & HasUser()

    # Модель отвечает секундами: ждать её в handle значило бы держать сессию БД и слот
    # диспетчера, поэтому сам запрос — в after_handle.
    incoming: Incoming | None = None

    async def handle(self) -> None:
        message = self.ctx.message
        roast = self.ctx.roast_service
        if message.chat.type not in GROUP_CHATS:
            return

        replied = message.reply_to_message
        to_bot = replied is not None and replied.user is not None and roast.is_bot(replied.user.id)
        if not roast.wants(message.chat.id, message.user.id, message.text, replied_to_bot=to_bot):
            return

        self.incoming = Incoming(
            chat_id=message.chat.id,
            telegram_id=message.user.id,
            first_name=message.user.first_name,
            text=message.text,
            replied=roast.replied(
                message.chat.id, replied.message_id, replied.text or replied.caption or ""
            )
            if replied is not None and to_bot
            else None,
        )

    async def after_handle(self) -> None:
        incoming = self.incoming
        if incoming is None:
            return

        roast = self.ctx.roast_service
        outcome = await roast.respond(incoming)
        if outcome.bored:
            await self.ctx.message.reply(self.ctx.text(Dialogs.roast.bored()))
            return
        if outcome.reply is None or outcome.log_id is None:
            return

        sent = await self.ctx.message.reply(outcome.reply)
        await roast.sent(incoming.chat_id, sent.message_id, incoming.first_name, outcome.log_id)


class RoastRouter(BaseRouter[AppContext]):
    handlers = (RoastHandler,)
