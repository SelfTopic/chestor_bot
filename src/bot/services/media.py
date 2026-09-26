import logging
import random
from pathlib import Path

from ..config import game_config
from ..exceptions import CollectionNotFoundError
from ..repositories import MediaRepository
from ..types import MediaCollection

logger = logging.getLogger(name=__name__)


class CollectionParser:
    MAP = {
        "snap": MediaCollection.SNAP_FINGER,
        "snap finger": MediaCollection.SNAP_FINGER,
        "kagune ukaku": MediaCollection.UPGRADE_KAGUNE_UKAKU,
        "kagune koukaku": MediaCollection.UPGRADE_KAGUNE_KOUKAKU,
        "kagune rinkaku": MediaCollection.UPGRADE_KAGUNE_RINKAKU,
        "kagune bikaku": MediaCollection.UPGRADE_KAGUNE_BIKAKU,
        "coffee": MediaCollection.COFFEE,
        "eat human": MediaCollection.EAT_HUMAN,
        "death": MediaCollection.DEATH,
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
    def __init__(self, media_repository: MediaRepository) -> None:
        self.media_repository = media_repository

    async def get_random_lottery_video(
        self, color_folder: str | None = None
    ) -> Path | None:
        lottery_folder = Path(game_config.path_to_assets) / "videos" / "lottery"

        if not lottery_folder.exists():
            logger.warning(f"Папка с лотерейными видео не найдена: {lottery_folder}")
            return None

        if color_folder is None:
            color_folders = [d for d in lottery_folder.iterdir() if d.is_dir()]
            if not color_folders:
                logger.warning(f"Папки с цветами не найдены в {lottery_folder}")
                return None
            color_folder = random.choice(color_folders).name

        color_path = lottery_folder / color_folder

        if not color_path.exists():
            logger.warning(f"Папка цвета не найдена: {color_path}")
            return None

        video_files = [
            f
            for f in color_path.iterdir()
            if f.is_file() and f.suffix.lower() in [".mp4", ".gif", ".webm", ".mov"]
        ]

        if not video_files:
            logger.warning(f"Видео файлы в папке {color_path} не найдены")
            return None

        video_path = random.choice(video_files)
        logger.debug(f"Выбрано видео для лотереи ({color_folder}): {video_path}")

        return video_path

    async def update_telegram_file_id(self, path: str, new_file_id: str):
        await self.media_repository.update_file_id(path=path, new_file_id=new_file_id)
