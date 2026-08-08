import logging
import re
from enum import Enum
from pathlib import Path
from typing import Optional

from pyrogram.client import Client
from pyrogram.types import Message

from .config import config

logger = logging.getLogger(__name__)

# Регулярка для парсинга капшена
# Пример: "Токийский гуль 1 сезон 1. Вкус"
CAPTION_PATTERN = re.compile(r"Токийский гуль\s+(\d+)\s+сезон\s+(\d+)\.\s+(.+)")


class ParseResult(Enum):
    SUCCESS = "Все серии скачаны"
    PARTIAL = "Часть серий скачана"
    FAILED = "Ошибка при скачивании"
    NO_MESSAGES = "В канале нет сообщений"
    ALREADY_EXISTS = "Все серии уже есть"


class TelegramParser:
    def __init__(self, app: Client):
        self.app = app
        self.download_path = Path(config.DOWNLOAD_PATH)
        self.download_path.mkdir(parents=True, exist_ok=True)

    def get_missing_series(self) -> set[tuple[int, int]]:
        """Возвращает множество (season, episode) которых нет в папке"""
        missing = set()

        for season in range(1, config.SEASONS_COUNT + 1):
            for episode in range(1, config.SERIES_COUNT + 1):
                file_name = f"Season_{season}_Episode_{episode}.mp4"
                if not (self.download_path / file_name).exists():
                    missing.add((season, episode))

        return missing

    def parse_caption(self, caption: str) -> Optional[tuple[int, int, str]]:
        """Парсит капшен, возвращает (season, episode, episode_name) или None"""
        match = CAPTION_PATTERN.search(caption)
        if not match:
            return None
        return int(match.group(1)), int(match.group(2)), match.group(3)

    async def get_channel_messages(
        self, channel_id: int, limit: int = 1000
    ) -> list[Message]:
        """Получает все сообщения из канала"""
        result_messages = []
        try:
            messages = self.app.get_chat_history(channel_id, limit=limit)

            if messages is None:
                logger.warning("В канале нет сообщений")
                return []

            async for message in messages:
                if message.media:  # Только сообщения с медиа
                    result_messages.append(message)

        except Exception as e:
            logger.error(f"Ошибка при получении сообщений: {e}")

        logger.info(f"Result messages: {result_messages}")
        return result_messages

    async def download_series(
        self, message: Message, season: int, episode: int
    ) -> bool:
        """Скачивает одну серию. Возвращает True если успешно"""
        file_path = self.download_path / f"Season_{season}_Episode_{episode}.mp4"

        try:
            await message.download(str(file_path))
            logger.info(f"Скачано: {season}x{episode}")
            return True
        except Exception as e:
            logger.error(f"Ошибка скачивания {season}x{episode}: {e}")
            # Удаляем частично скачанный файл
            if file_path.exists():
                file_path.unlink()
            return False

    async def parse_channel(self) -> ParseResult:
        """Основной метод парсинга"""
        # 1. Проверяем, что уже скачано
        missing_series = self.get_missing_series()
        if not missing_series:
            logger.info("Все серии уже скачаны")
            return ParseResult.ALREADY_EXISTS

        logger.info(f"Недостающие серии: {len(missing_series)} шт.")

        # 2. Получаем сообщения из канала
        channel_id = config.CHANNEL_ID
        messages = await self.get_channel_messages(channel_id)

        if not messages:
            logger.warning("В канале нет сообщений")
            return ParseResult.NO_MESSAGES

        # 3. Обрабатываем сообщения
        downloaded_count = 0

        for message in messages:
            if not message.caption:
                continue

            parsed = self.parse_caption(message.caption)
            if not parsed:
                continue

            season, episode, episode_name = parsed

            # Проверяем, нужно ли скачивать
            if (season, episode) not in missing_series:
                continue

            # Скачиваем
            success = await self.download_series(message, season, episode)
            if success:
                missing_series.remove((season, episode))
                downloaded_count += 1

            # Если всё скачали — выходим
            if not missing_series:
                break

        # 4. Результат
        if downloaded_count == 0:
            return ParseResult.FAILED
        elif missing_series:
            logger.info(f"Скачано {downloaded_count}, осталось {len(missing_series)}")
            return ParseResult.PARTIAL
        else:
            logger.info(f"Все {downloaded_count} серий скачаны!")
            return ParseResult.SUCCESS
