class UserNotFound(Exception):
    def __init__(self, username: str) -> None:
        super().__init__(username)
        self.username = username
