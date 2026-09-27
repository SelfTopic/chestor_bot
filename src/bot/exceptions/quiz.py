class QuizUnavailable(Exception): ...


class QuizEmailMissing(QuizUnavailable): ...


class QuizSessionMissing(QuizUnavailable):
    def __init__(self, email: str) -> None:
        super().__init__(email)
        self.email = email
