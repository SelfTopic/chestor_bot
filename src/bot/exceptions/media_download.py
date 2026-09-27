class MediaError(Exception):
    pass


class MediaNotFoundError(MediaError):
    pass


class CollectionNotFoundError(MediaError):
    def __init__(self, collection: str, supported: list[str]) -> None:
        super().__init__(collection)
        self.collection = collection
        self.supported = supported


class InvalidMediaRequestError(MediaError):
    pass


class ValidationMediaError(MediaError):
    pass
