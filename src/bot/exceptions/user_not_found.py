class UserNotFound(Exception):
    """Common base class for not found users"""

    def __init__(self, message: str = "Пользователь не найден") -> None:
        super().__init__(message)


class UserNotFoundInDatabase(UserNotFound):
    def __init__(self, message: str = "Пользователь не найден в базе данных") -> None:
        super().__init__(message)


class UserNotFoundInChat(UserNotFound):
    def __init__(self, message: str = "Пользователь не найден в чате") -> None:
        super().__init__(message)


class UserNotFoundInMessage(UserNotFound):
    def __init__(
        self, message: str = "В сообщении не удалось определить пользователя"
    ) -> None:
        super().__init__(message)
