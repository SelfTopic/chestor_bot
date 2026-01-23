from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...exceptions import CollectionNotFoundError, MediaNotFoundError
from ...services import MediaService

router = Router(name=__name__)


@router.message(Command("add_gif"))
@inject
async def add_gif(
    message: Message,
    command: CommandObject,
    media_service: MediaService = Provide[Container.media_service],
) -> None:
    if not message.reply_to_message:
        raise MediaNotFoundError(
            "Эта команда используется в ответ на гиф для скачивания"
        )

    if not message.reply_to_message.animation:
        raise MediaNotFoundError("В выбранном вами сообщении отсутствует гиф")

    args = command.args

    if not args:
        raise CollectionNotFoundError("Нет указателей для медиа")

    path = await media_service.download_from_message(
        message=message.reply_to_message, collection_args=args
    )
    if not path.exists():
        await message.reply("А путь неправильный")

    if not path.is_file():
        await message.reply(f"Ошибка: {path} не является файлом.")
        return

    if path.stat().st_size == 0:
        await message.reply("Ошибка: Скачанный файл пуст.")
        return

    await message.answer_animation(
        animation=FSInputFile(path),
        caption=f"Эта гиф успешено скачана в путь {path}",
    )
