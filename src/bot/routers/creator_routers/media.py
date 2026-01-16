from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

router = Router(name=__name__)


@router.message(Command("/add_gif"))
async def add_gif(message: Message, command: CommandObject) -> None:
    args = command.args

    if not args:
        await message.reply("Нет указателей для медиа")
        return None

    args = args.split()

    type_gif = args[0]

    # TODO - Нужно скачать гиф и сохранить в нужную папку в assets/, но для этого нужно написать сервис для скачивания, инициализации и тд.
