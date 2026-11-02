from enum import Enum, auto


class NicknameProblem(Enum):
    EMPTY = auto()
    TOO_LONG = auto()
    LINK = auto()


class NicknameRejected(Exception):
    def __init__(self, problem: NicknameProblem) -> None:
        super().__init__(problem.name)
        self.problem = problem
