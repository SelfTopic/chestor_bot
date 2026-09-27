class UserNotFound(Exception):
    def __init__(self, query: str) -> None:
        super().__init__(query)
        self.query = query
