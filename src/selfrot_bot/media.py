from typing import Any


class UnsupportedMediaDownloader:
    """
    Замена MediaDownloader (он держит aiogram Bot и качает файлы через bot.download).
    В selfrotgram скачивания файлов пока нет: сервисы, которым нужен только MediaService
    без скачивания (лотерея, кофе), работают, а сохранение чужого медиа честно падает.
    """

    async def download_media_from_message(self, message: Any) -> Any:
        raise NotImplementedError(
            "Скачивание файлов ещё не поддерживается в selfrotgram"
        )
