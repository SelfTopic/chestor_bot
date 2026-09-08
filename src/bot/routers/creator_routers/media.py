from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...exceptions import CollectionNotFoundError, MediaNotFoundError, UserNotFound
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

    if not message.from_user:
        raise UserNotFound()

    is_video = bool(message.reply_to_message.video)

    if not message.reply_to_message.animation and not is_video:
        raise MediaNotFoundError(
            "В выбранном вами сообщении отсутствует гиф или видео"
        )

    args = command.args

    if not args:
        raise CollectionNotFoundError("Нет указателей для медиа")

    path = await media_service.download_from_message(
        message=message.reply_to_message,
        collection_args=args,
        uploaded_by=message.from_user.id,
    )
    if not path.exists():
        await message.reply("А путь неправильный")

    if not path.is_file():
        await message.reply(f"Ошибка: {path} не является файлом.")
        return

    if path.stat().st_size == 0:
        await message.reply("Ошибка: Скачанный файл пуст.")
        return

    caption = f"Это медиа успешно скачано в путь {path}"
    if is_video:
        await message.answer_video(video=FSInputFile(path), caption=caption)
    else:
        await message.answer_animation(animation=FSInputFile(path), caption=caption)
