import logging
import random
from io import BytesIO
from pathlib import Path

import aiofiles
from aiogram import Bot
from aiogram.types import Message

from ..config import game_config
from ..exceptions import (
    CollectionNotFoundError,
    InvalidMediaRequestError,
    MediaError,
    ValidationMediaError,
)
from ..repositories import MediaRepository
from ..types import MediaCollection, MediaDownloadType, MediaSaveRequest
from ..types.insert import MediaInsert

logger = logging.getLogger(name=__name__)


class MediaDownloader:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def download_media_from_message(self, message: Message) -> MediaSaveRequest:
        bytes_media = None
        type_media = None
        original_filename = None
        file_id = None
        io_object = BytesIO()

        if message.animation:
            bytes_media = await self._bot.download(
                file=message.animation.file_id, destination=io_object
            )
            file_id = message.animation.file_id
            logger.debug(f"Downloaded data: {bytes_media}")
            type_media = MediaDownloadType.ANIMATION
            original_filename = f"{type_media.value}_{file_id}"

        elif message.video:
            bytes_media = await self._bot.download(
                file=message.video.file_id, destination=io_object
            )
            file_id = message.video.file_id
            type_media = MediaDownloadType.VIDEO
            original_filename = f"{type_media.value}_{file_id}"

        elif message.photo:
            bytes_media = await self._bot.download(
                file=message.photo[-1].file_id, destination=io_object
            )
            file_id = message.photo[-1].file_id
            type_media = MediaDownloadType.PHOTO
            original_filename = f"{type_media.value}_{file_id}"

        if not bytes_media:
            raise MediaError("Байты в медиа не найдены")

        bytes_media.seek(0)

        return MediaSaveRequest(
            bytes_media=bytes_media.read(),
            type_media=type_media,
            original_filename=original_filename,
            file_id=file_id,
        )


class CollectionParser:
    MAP = {
        "snap": MediaCollection.SNAP_FINGER,
        "snap finger": MediaCollection.SNAP_FINGER,
        "kagune ukaku": MediaCollection.UPGRADE_KAGUNE_UKAKU,
        "kagune koukaku": MediaCollection.UPGRADE_KAGUNE_KOUKAKU,
        "kagune rinkaku": MediaCollection.UPGRADE_KAGUNE_RINKAKU,
        "kagune bikaku": MediaCollection.UPGRADE_KAGUNE_BIKAKU,
        "coffee": MediaCollection.COFFEE,
        "welcome gif": MediaCollection.WELCOME_GIF,
        "welcome photo": MediaCollection.WELCOME_PHOTO,
        "welcome video": MediaCollection.WELCOME_VIDEO,
        "goodbye gif": MediaCollection.GOODBYE_GIF,
        "goodbye photo": MediaCollection.GOODBYE_PHOTO,
        "goodbye video": MediaCollection.GOODBYE_VIDEO,
    }

    @classmethod
    def parse(cls, args: str) -> MediaCollection:
        if args in cls.MAP:
            return cls.MAP[args]

        raise CollectionNotFoundError(
            f"Коллекция {args} не найдена. Список поддерживаемых коллекций: {[i for i in cls.MAP.keys()]}"
        )


class MediaService:
    def __init__(
        self,
        downloader: MediaDownloader,
        media_repository: MediaRepository,
        parser: CollectionParser = CollectionParser(),
    ) -> None:
        self._downloader = downloader
        self._parser = parser
        self.media_repository = media_repository

    async def get_random_gif(self, collection_string: str):
        collection = self._parser.parse(collection_string)
        type_media = MediaDownloadType.ANIMATION

        media_request = MediaSaveRequest(type_media=type_media, collection=collection)

        folder_path = self._generate_path(media_save_request=media_request)
        folder_path.mkdir(parents=True, exist_ok=True)
        files = [f for f in folder_path.iterdir() if f.is_file()]

        file_path = random.choice(files) if files else None

        logger.debug(f"Generated path to media: {file_path}")

        media = await self.media_repository.get_by_path(path=str(file_path))

        if not media:
            return None

        return media

    async def update_telegram_file_id(self, path: str, new_file_id: str):
        await self.media_repository.update_file_id(path=path, new_file_id=new_file_id)

    async def download_from_message(
        self, message: Message, collection_args: str, uploaded_by: int
    ):
        media_request = await self._downloader.download_media_from_message(
            message=message
        )

        if (
            not media_request.bytes_media
            or not media_request.type_media
            or not media_request.file_id
        ):
            raise InvalidMediaRequestError("В сообщении не найдено медиа")

        collection = self._parser.parse(collection_args)

        media_request.collection = collection

        path = await self._async_save_media(media_save_request=media_request)

        media_insert = MediaInsert(
            media_type=media_request.type_media.value,
            telegram_file_id=media_request.file_id,
            collection=collection.value,
            path=str(path),
            uploaded_by=uploaded_by,
        )

        exists = await self.media_repository.exists_by_path(str(path))

        if exists:
            raise MediaError("Запись в базе данных с таким файлом уже существует")

        await self.media_repository.insert(media_insert=media_insert)

        return path

    def _validate_media_request(self, media_request: MediaSaveRequest):
        if not media_request.bytes_media:
            raise ValidationMediaError("Ошибка валидации: не найдены байты в медиа")

        if not media_request.collection:
            raise ValidationMediaError("Ошибка валидации: не найдена коллекция медиа")

        if not media_request.original_filename:
            raise ValidationMediaError(
                "Ошибка валидации: не найдено имя для скачиваемого медиа"
            )

        if not media_request.type_media:
            raise ValidationMediaError(
                "Ошибка валидации: не найден тип скачиваемого медиа"
            )

    async def _async_save_media(self, media_save_request: MediaSaveRequest):
        EXT_MAP = {
            MediaDownloadType.ANIMATION: ".mp4",
            MediaDownloadType.PHOTO: ".png",
            MediaDownloadType.VIDEO: ".mp4",
        }

        self._validate_media_request(media_request=media_save_request)

        if (
            not media_save_request.bytes_media
            or not media_save_request.type_media
            or not media_save_request.original_filename
        ):
            raise InvalidMediaRequestError("Не найдены байты или тип файла в медиа")
        folder_path = Path(self._generate_path(media_save_request=media_save_request))
        folder_path.mkdir(parents=True, exist_ok=True)

        filename_raw = Path(media_save_request.original_filename).stem

        target_ext = EXT_MAP.get(media_save_request.type_media, ".bin")

        final_file_path = folder_path / f"{filename_raw}{target_ext}"

        async with aiofiles.open(final_file_path, "wb") as file:
            await file.write(media_save_request.bytes_media)

        return final_file_path

    def _generate_path(self, media_save_request: MediaSaveRequest):
        if not media_save_request.collection or not media_save_request.type_media:
            raise InvalidMediaRequestError(
                "Не указаны коллекция или тип медиа в запросе медиа"
            )

        type_media = media_save_request.collection.sub_type

        collection = media_save_request.collection.category
        collection_double = None

        if "kagune" in media_save_request.collection.value:
            type_media = MediaDownloadType.ANIMATION.value
            collection_double = media_save_request.collection.sub_type

        return (
            Path(game_config.path_to_assets)
            / type_media
            / collection
            / (collection_double or "")
        )
