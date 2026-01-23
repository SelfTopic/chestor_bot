class MediaError(Exception):
    pass


class MediaNotFoundError(MediaError):
    pass


class CollectionNotFoundError(MediaError):
    pass


class InvalidMediaRequestError(MediaError):
    pass


class ValidationMediaError(MediaError):
    pass
