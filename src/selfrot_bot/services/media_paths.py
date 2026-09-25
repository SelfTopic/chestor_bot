"""
Куда на диске ложится медиа коллекции и как найти уже сохранённый файл — общее для
/add_gif и NotificationTicker (обоим нужно одно и то же имя папки и та же логика
подбора случайного файла, порознь они бы неизбежно разошлись). Ничего из этого не
знает про Telegram-библиотеку: только диск, БД (через MediaRepository) и доменные
типы src.bot (CollectionParser/MediaCollection/MediaDownloadType), которые сами не
завязаны на aiogram.
"""

import random
from pathlib import Path

from src.bot.config import game_config
from src.bot.repositories import MediaRepository
from src.bot.services.media import CollectionParser
from src.bot.types import MediaCollection, MediaDownloadType
from src.bot.types.insert import MediaInsert
from src.database.models import Media

EXTENSION = {MediaDownloadType.ANIMATION: ".mp4", MediaDownloadType.VIDEO: ".mp4"}


def collection_folder(
    type_media: MediaDownloadType, collection: MediaCollection
) -> Path:
    """Тот же путь, что строил MediaService._generate_path: для "kagune"-коллекций
    подпапка — сам тип кагуне (sub_type), для остальных её нет."""
    subfolder = collection.sub_type if "kagune" in collection.value else ""
    return (
        Path(game_config.path_to_assets)
        / type_media.value
        / collection.category
        / subfolder
    )


async def random_media(
    media_repository: MediaRepository,
    type_media: MediaDownloadType,
    collection_string: str,
    registered_by: int,
) -> Media | None:
    """
    Случайный уже сохранённый файл коллекции (через /add_gif), или None, если в папке
    ничего нет. Файл, лежащий на диске, но ещё не заведённый в БД (положен вручную),
    регистрируется на лету — тот же приём, что у MediaService._get_random_media.
    """
    collection = CollectionParser.parse(collection_string)
    folder = collection_folder(type_media, collection)
    folder.mkdir(parents=True, exist_ok=True)

    files = [f for f in folder.iterdir() if f.is_file()]
    if not files:
        return None

    file_path = random.choice(files)
    media = await media_repository.get_by_path(str(file_path))
    if media is not None:
        return media

    return await media_repository.insert(
        MediaInsert(
            media_type=type_media.value,
            telegram_file_id=None,
            collection=collection.value,
            path=str(file_path),
            uploaded_by=registered_by,
        )
    )
