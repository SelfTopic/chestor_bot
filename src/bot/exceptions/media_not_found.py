class MediaNotFound(Exception):
    """Common base class for not found chats"""


class MediaNotFoundInDatabase(MediaNotFound): ...
