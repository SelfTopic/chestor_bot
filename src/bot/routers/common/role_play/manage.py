from typing import Annotated

from pydantic import AfterValidator
from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from src.bot.dialogs import Dialogs
from src.bot.exceptions import RpCommandLimitReached, RpCommandNotFound
from src.bot.types.rp_commands import TypeRpCommandEnum

from ....context import AppContext
from ...types import CaptionMessage, TextMessage
from .filters import SetRpOnMedia
from .sending import send_rp


class NewRpOnMediaHandler(MessageHandler[AppContext[CaptionMessage]]):
    query = SetRpOnMedia()
    usage = Dialogs.rp.media_usage()

    @staticmethod
    def parse_caption(caption: str) -> tuple[str, str] | None:
        args = caption.lower().split()
        if len(args) < 3:
            return None

        return args[1], " ".join(args[2:])

    async def handle(self) -> None:
        message = self.ctx.message

        parsed = self.parse_caption(message.caption)
        if parsed is None:
            await self.ctx.say(self.usage, reply=True)
            return

        command, action = parsed

        if message.photo:
            type_command = TypeRpCommandEnum.PHOTO
            file_id = message.photo[-1].file_id
        elif message.animation:
            type_command = TypeRpCommandEnum.ANIMATION
            file_id = message.animation.file_id
        else:
            raise RuntimeError("Неподдерживаемый тип медиа для RP-команды")

        rp = await self.ctx.rp_commands_service.insert(
            chat_id=message.chat.id,
            command=command,
            action=action,
            type_command=type_command,
            file_id=file_id,
        )

        await send_rp(
            message,
            type_command,
            file_id,
            self.ctx.text(Dialogs.rp.created(command=rp.command, action=rp.action)),
        )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, RpCommandLimitReached):
            await self.ctx.say(Dialogs.rp.limit_reached(limit=exc.limit))
            return

        raise exc


def _squash_spaces(value: str) -> str:
    return " ".join(value.split())


Action = Annotated[Rest, AfterValidator(_squash_spaces)]


class SetRpArgs(CommandArgs):
    command: str
    action: Action


class NewRpHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("set_rp", SetRpArgs)
    query = cmd
    usage = Dialogs.rp.set_usage()

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)

        rp = await self.ctx.rp_commands_service.insert(
            chat_id=self.ctx.message.chat.id,
            command=args.command,
            action=args.action,
            type_command=TypeRpCommandEnum.TEXT,
        )

        await self.ctx.say(Dialogs.rp.created(command=rp.command, action=rp.action))

    async def on_error(self, exc: Exception) -> None:
        match exc:
            case CommandArgsError():
                line = self.usage
            case RpCommandLimitReached(limit=limit):
                line = Dialogs.rp.limit_reached(limit=limit)
            case _:
                raise exc
        await self.ctx.say(line)


class GetAllRpHandler(MessageHandler[AppContext[TextMessage]]):
    query = Command("all_rp")

    async def handle(self) -> None:
        message = self.ctx.message
        all_rp = await self.ctx.rp_commands_service.get_all(chat_id=message.chat.id)

        if len(all_rp) == 0:
            await self.ctx.say(Dialogs.rp.empty(), reply=True)
            return

        rows = "\n".join(
            self.ctx.text(
                Dialogs.rp.row(place=place, command=rp.command, action=rp.action)
            )
            for place, rp in enumerate(all_rp, start=1)
        )
        await self.ctx.say(Dialogs.rp.list(rows=rows))


class DelRpArgs(CommandArgs):
    command: Rest


class DeleteRpHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("del_rp", DelRpArgs)
    query = cmd
    usage = Dialogs.rp.delete_usage()

    async def handle(self) -> None:
        command = self.cmd.parse(self.ctx).command

        message = self.ctx.message
        await self.ctx.rp_commands_service.delete(
            chat_id=message.chat.id, command=command
        )

        await self.ctx.say(Dialogs.rp.deleted(command=command), reply=True)

    async def on_error(self, exc: Exception) -> None:
        match exc:
            case CommandArgsError():
                line = self.usage
            case RpCommandNotFound():
                line = Dialogs.rp.not_found()
            case _:
                raise exc
        await self.ctx.say(line)
