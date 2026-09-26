"""Управление Role-Play командами чата: добавить (текстом или с фото/гифкой), список, удалить."""

from typing import Annotated

from pydantic import AfterValidator
from selfrot import CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError
from selfrot.filter import Command

from src.bot.exceptions import RpCommandValidateError
from src.bot.types.rp_commands import TypeRpCommandEnum

from ....context import AppContext
from ...types import CaptionMessage, TextMessage
from .filters import SetRpOnMedia
from .sending import send_rp


class NewRpOnMediaHandler(MessageHandler[AppContext[CaptionMessage]]):
    query = SetRpOnMedia()

    @staticmethod
    def parse_caption(caption: str) -> tuple[str, str] | None:
        """`/set_rp команда действие...` -> (команда, действие); None, если слов мало.
        Command читает только message.text, а у медиа команда лежит в подписи."""
        args = caption.lower().split()
        if len(args) < 3:
            return None

        return args[1], " ".join(args[2:])

    async def handle(self) -> None:
        message = self.ctx.message

        parsed = self.parse_caption(message.caption)
        if parsed is None:
            await message.reply("Используйте\n/set_rp\n<команда>\n<действие>")
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
            f"Установлена Role-Play команда {rp.command} с действием {rp.action}",
        )


def _squash_spaces(value: str) -> str:
    return " ".join(value.split())


Action = Annotated[Rest, AfterValidator(_squash_spaces)]


class SetRpArgs(CommandArgs):
    command: str
    action: Action  # всё остальное; переводы строк и повторы пробелов схлопнуты


class NewRpHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("set_rp", SetRpArgs)
    query = cmd
    usage = (
        "Используйте как /set_rp\n<команда>\n<действие>\nнапример:\n"
        "/set_rp\nпогладить\nпогладила(-а) по головке"
    )

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)

        rp = await self.ctx.rp_commands_service.insert(
            chat_id=self.ctx.message.chat.id,
            command=args.command,
            action=args.action,
            type_command=TypeRpCommandEnum.TEXT,
        )

        await self.ctx.message.answer(
            f"Установлена Role-Play команда {rp.command} с действием {rp.action}"
        )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            # дальше, как у прода: текст ошибки уйдёт пользователем через on_error диспетчера
            raise RpCommandValidateError(self.usage) from exc

        raise exc


class GetAllRpHandler(MessageHandler[AppContext[TextMessage]]):
    query = Command("all_rp")

    async def handle(self) -> None:
        message = self.ctx.message
        all_rp = await self.ctx.rp_commands_service.get_all(chat_id=message.chat.id)

        if len(all_rp) == 0:
            await message.reply("В этом чате нет Role-Play команд. Используйте /set_rp")
            return

        answer_text = "Список всех Role-Play команд чата: \n\n"

        for index, rp in enumerate(all_rp, start=1):
            answer_text += f"{index}. {rp.command} - {rp.action}\n"

        await message.answer(answer_text)


class DelRpArgs(CommandArgs):
    command: Rest


class DeleteRpHandler(MessageHandler[AppContext[TextMessage]]):
    cmd = Command("del_rp", DelRpArgs)
    query = cmd
    usage = "не указаны аргументы для удаления. используйте /del_rp <command>"

    async def handle(self) -> None:
        command = self.cmd.parse(self.ctx).command

        message = self.ctx.message
        await self.ctx.rp_commands_service.delete(
            chat_id=message.chat.id, command=command
        )

        await message.reply(f"Role-Play команда {command} удалена")

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            raise RpCommandValidateError(self.usage) from exc

        raise exc
