class WordleGuessError(Exception): ...


class WordleWrongLength(WordleGuessError):
    def __init__(self, length: int) -> None:
        super().__init__(length)
        self.length = length


class WordleNotRussian(WordleGuessError): ...
