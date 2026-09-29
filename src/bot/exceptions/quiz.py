class QuizUnavailable(Exception): ...


class QuizEmailMissing(QuizUnavailable): ...


class QuizSessionMissing(QuizUnavailable):
    def __init__(self, email: str) -> None:
        super().__init__(email)
        self.email = email


class QuizBusy(QuizUnavailable):
    def __init__(self, retry_after: int) -> None:
        super().__init__(retry_after)
        self.retry_after = retry_after
