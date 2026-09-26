"""
/add_gif: сохранить гиф или видео (в ответ на сообщение) в библиотеку медиа под нужной
коллекцией. Раньше требовало aiogram Bot (MediaDownloader) — теперь скачивание делает
ctx.download() (selfrotgram 0.1.4+). Разбор коллекции, путь на диск и запись в БД — та же
доменная логика, что у прода (CollectionParser, game_config), она не трогала aiogram и
раньше.
"""

from pathlib import Path

from selfrot import BaseRouter, CommandArgs, MessageHandler, Rest
from selfrot.exceptions import CommandArgsError, ContextError
from selfrot.filter import Command, HasReplyToMessage, HasUser
from selfrot.types import InputFile

from src.bot.exceptions import CollectionNotFoundError
from src.bot.services.media import CollectionParser
from src.bot.types import MediaCollection, MediaDownloadType
from src.bot.types.insert import MediaInsert

from ...context import AppContext
from ...services.media_paths import EXTENSION, collection_folder
from ..types import TextUserReplyToMessage

USAGE = "Эта команда используется в ответ на гиф или видео: /add_gif <коллекция>"


def target_path(
    type_media: MediaDownloadType,
    collection: MediaCollection,
    file_id: str,
) -> Path:
    """
    Полный путь до файла (папка из collection_folder + детерминированное имя).
    Отдельная функция — её можно проверить без диска и без апдейта (в отличие от
    самой папки, которую могут не разрешить создать: часть src/assets в этом
    окружении принадлежит другому пользователю).
    """
    return (
        collection_folder(type_media, collection)
        / f"{type_media.value}_{file_id}{EXTENSION[type_media]}"
    )


class AddGifArgs(CommandArgs):
    collection: Rest  # многословные имена коллекций: "kagune ukaku", "welcome gif"


class AddGifHandler(MessageHandler[AppContext[TextUserReplyToMessage]]):
    cmd = Command("add_gif", AddGifArgs)
    query = cmd & HasUser() & HasReplyToMessage()

    async def handle(self) -> None:
        args = self.cmd.parse(self.ctx)
        message = self.ctx.message
        reply = message.reply_to_message

        if reply.video:
            type_media, file_id = MediaDownloadType.VIDEO, reply.video.file_id
        elif reply.animation:
            type_media, file_id = MediaDownloadType.ANIMATION, reply.animation.file_id
        else:
            await message.reply("В выбранном вами сообщении отсутствует гиф или видео")
            return

        try:
            collection = CollectionParser.parse(args.collection)
        except CollectionNotFoundError as e:
            await message.reply(str(e))
            return

        destination = target_path(type_media, collection, file_id)
        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            path = await self.ctx.download(destination)
        except ContextError:
            await message.reply(USAGE)
            return

        if await self.ctx.media_repository.exists_by_path(str(path)):
            await message.reply("Запись в базе данных с таким файлом уже существует")
            return

        await self.ctx.media_repository.insert(
            MediaInsert(
                media_type=type_media.value,
                telegram_file_id=file_id,
                collection=collection.value,
                path=str(path),
                uploaded_by=message.user.id,
            )
        )

        caption = f"Это медиа успешно скачано в путь {path}"
        if type_media == MediaDownloadType.VIDEO:
            await message.answer_video(video=InputFile.from_path(path), caption=caption)
        else:
            await message.answer_animation(
                animation=InputFile.from_path(path), caption=caption
            )

    async def on_error(self, exc: Exception) -> None:
        if isinstance(exc, CommandArgsError):
            await self.ctx.message.reply(USAGE)
            return

        raise exc


class MediaRouter(BaseRouter[AppContext]):
    handlers = (AddGifHandler,)
