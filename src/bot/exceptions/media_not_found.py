class MediaNotFound(Exception):
    def __init__(self, message: str = "Медиа не найдено") -> None:
        super().__init__(message)


class MediaNotFoundInDatabase(MediaNotFound):
    def __init__(self, message: str = "Медиа не найдено в базе данных") -> None:
        super().__init__(message)
