class ChatNotFound(Exception):
    """Common base class for not found chats"""

    def __init__(self, message: str = "Чат не найден") -> None:
        super().__init__(message)


class ChatNotFoundInDatabase(ChatNotFound):
    def __init__(self, message: str = "Чат не найден в базе данных") -> None:
        super().__init__(message)


class ChatNotFoundInMessage(ChatNotFound):
    def __init__(self, message: str = "В сообщении не удалось определить чат") -> None:
        super().__init__(message)
