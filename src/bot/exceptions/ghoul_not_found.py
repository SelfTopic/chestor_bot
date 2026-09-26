class GhoulNotFound(Exception):
    def __init__(self, message: str = "Гуль не найден") -> None:
        super().__init__(message)


class GhoulNotFoundInDatabase(GhoulNotFound):
    def __init__(self, message: str = "Гуль не найден в базе данных") -> None:
        super().__init__(message)
