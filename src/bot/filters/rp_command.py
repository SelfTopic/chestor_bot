from typing import Any

from aiogram.filters import Filter
from aiogram.types import Message
from dependency_injector.wiring import Provide

from src.bot.containers import Container
from src.bot.services import RpCommandsService


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


__all__ = ["RpCommandFilter"]
