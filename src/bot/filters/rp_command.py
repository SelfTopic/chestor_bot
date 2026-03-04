from typing import Any

from aiogram.filters import Filter
from aiogram.types import Message
from dependency_injector.wiring import Provide

from src.bot.containers import Container
from src.bot.services import RpCommandsService
from src.bot.types.rp_commands import TypeRpCommandEnum


class RpCommandFilter(Filter):
    async def __call__(
        self,
        message: Message,
        rp_commands_service: RpCommandsService = Provide[Container.rp_commands_service],
    ) -> bool | dict[str, Any]:
        if not message.text:
            return False

        rp_commands = await rp_commands_service.get_all(message.chat.id)
        command_text = message.text.lower().split()[0]
        for rp in rp_commands:
            if rp.command.lower() == command_text:
                return {"rp_command": rp}
        return False


class NewRpCommandOnMedia(Filter):
    def __init__(self, type_command: TypeRpCommandEnum) -> None:
        self.type_command = type_command

    async def __call__(
        self,
        message: Message,
    ) -> bool | dict[str, Any]:
        if self.type_command == TypeRpCommandEnum.PHOTO and not message.photo:
            return False

        if self.type_command == TypeRpCommandEnum.ANIMATION and not message.animation:
            return False

        if not message.caption:
            return False

        args = message.caption.lower().split()

        if args[0] != "/set_rp":
            return False

        if len(args) < 3:
            await message.reply("Используйте\n/set_rp\n<команда>\n<действие>")
            return False

        command = args[1]
        action = " ".join(args[2:])

        return {
            "command": command,
            "action": action,
            "type_command": self.type_command,
        }


__all__ = [
    "RpCommandFilter",
    "NewRpCommandOnMedia",
]
