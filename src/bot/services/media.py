import logging

from ..exceptions import CollectionNotFoundError
from ..repositories import MediaRepository
from ..types import MediaCollection

logger = logging.getLogger(name=__name__)


class CollectionParser:
    MAP = {
        "death": MediaCollection.DEATH,
        "welcome gif": MediaCollection.WELCOME_GIF,
        "welcome photo": MediaCollection.WELCOME_PHOTO,
        "welcome video": MediaCollection.WELCOME_VIDEO,
        "goodbye gif": MediaCollection.GOODBYE_GIF,
        "goodbye photo": MediaCollection.GOODBYE_PHOTO,
        "goodbye video": MediaCollection.GOODBYE_VIDEO,
    }

    @classmethod
    def parse(cls, args: str) -> MediaCollection:
        if args in cls.MAP:
            return cls.MAP[args]

        raise CollectionNotFoundError(args, list(cls.MAP))


class MediaService:
    def __init__(self, media_repository: MediaRepository) -> None:
        self.media_repository = media_repository
