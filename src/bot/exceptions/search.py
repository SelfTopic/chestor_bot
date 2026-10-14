class SearchError(Exception): ...


class SearchUnavailable(SearchError): ...


class SearchLimitReached(SearchError): ...


class SearchCooldown(SearchError):
    def __init__(self, seconds: int) -> None:
        super().__init__(seconds)
        self.seconds = seconds
