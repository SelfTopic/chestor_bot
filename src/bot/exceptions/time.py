class DurationParseError(Exception):
    """Ошибка парсинга строкового значения времени"""

    def __init__(self, message: str = "Не удалось распознать длительность") -> None:
        super().__init__(message)
