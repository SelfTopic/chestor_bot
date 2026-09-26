"""Использование Role-Play команды: «погладить» в ответ на сообщение или «погладить @user»."""

from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.filter import HasUser

from ....context import AppContext
from ...types import TextUserMessage
from .filters import RpCommandFilter
from .sending import send_rp


class RpArgs(CommandArgs):
    """«погладить @username». В ответ на сообщение адресат известен и аргументы не нужны."""

    target: str = ""  # «@username», если команда без ответа на сообщение
    note: Rest = ""  # «погладить @user нежно»: остаток игнорируется


class RolePlayHandler(MessageHandler[AppContext[TextUserMessage]]):
    rp_filter = RpCommandFilter(RpArgs)
    query = rp_filter & HasUser()

    async def handle(self) -> None:
        message = self.ctx.message

        found = await self.rp_filter.find(self.ctx)
        assert found is not None

        addressee = await self.ctx.addressee(found.command.parse(self.ctx).target)
        if addressee is None:
            return  # некому: без ответа и @username команда молчит

        rp_command = found.rp
        answer_text = (
            f"{message.user.first_name} {rp_command.action} {addressee.first_name}"
        )

        await send_rp(
            message,
            rp_command.type_command,
            rp_command.file_id,
            answer_text,
            quote=True,
        )
