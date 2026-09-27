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
    return Path(game_config.path_to_assets) / type_media.value / collection.category


def random_file(folder: Path) -> Path | None:
    if not folder.is_dir():
        return None
    files = [f for f in folder.iterdir() if f.is_file()]
    return random.choice(files) if files else None


async def media_for(
    media_repository: MediaRepository,
    path: Path,
    type_media: MediaDownloadType,
    collection: str,
    registered_by: int,
) -> Media:
    media = await media_repository.get_by_path(str(path))
    if media is not None:
        return media

    return await media_repository.insert(
        MediaInsert(
            media_type=type_media.value,
            telegram_file_id=None,
            collection=collection,
            path=str(path),
            uploaded_by=registered_by,
        )
    )


async def random_media(
    media_repository: MediaRepository,
    type_media: MediaDownloadType,
    collection_string: str,
    registered_by: int,
) -> Media | None:
    collection = CollectionParser.parse(collection_string)
    path = random_file(collection_folder(type_media, collection))
    if path is None:
        return None

    return await media_for(
        media_repository, path, type_media, collection.value, registered_by
    )
