from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import HasUser

from ...context import AppContext
from ..types import TextUserMessage
from .filters import RpCommandFilter
from .sending import send_rp


class RpArgs(CommandArgs):
    target: str = ""
    note: Rest = ""


class RolePlayHandler(MessageHandler[AppContext[TextUserMessage]]):
    rp_filter = RpCommandFilter(RpArgs)
    query = rp_filter & HasUser()

    async def handle(self) -> None:
        message = self.ctx.message

        found = await self.rp_filter.find(self.ctx)
        assert found is not None

        addressee = await self.ctx.addressee(found.command.parse(self.ctx).target)
        if addressee is None:
            return

        rp_command = found.rp
        actor = await self.ctx.name(message.user.id, message.user.first_name)
        answer_text = f"{actor} {rp_command.action} {addressee.name}"

        await send_rp(
            message,
            rp_command.type_command,
            rp_command.file_id,
            answer_text,
            quote=True,
        )
