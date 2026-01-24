from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MediaCollection(str, Enum):
    UPGRADE_KAGUNE_UKAKU = "upgrade_kagune:ukaku"
    UPGRADE_KAGUNE_KOUKAKU = "upgrade_kagune:koukaku"
    UPGRADE_KAGUNE_RINKAKU = "upgrade_kagune:rinkaku"
    UPGRADE_KAGUNE_BIKAKU = "upgrade_kagune:bikaku"
    SNAP_FINGER = "snap_finger:animation"
    COFFEE = "coffee:animation"
    FIGHT = "fight:animation"
    WELCOME_GIF = "welcome:animation"
    WELCOME_PHOTO = "welcome:photo"
    WELCOME_VIDEO = "welcome:video"
    GOODBYE_GIF = "goodbye:animation"
    GOODBYE_PHOTO = "goodbye:photo"
    GOODBYE_VIDEO = "goodbye:video"

    @property
    def category(self) -> str:
        return self.value.split(":")[0]

    @property
    def sub_type(self) -> str:
        return self.value.split(":")[-1]


class MediaDownloadType(str, Enum):
    ANIMATION = "animation"
    VIDEO = "video"
    STICKER = "sticker"
    PHOTO = "photo"
    VOICE = "voice"
    AUDIO = "audio"


@dataclass
class MediaSaveRequest:
    type_media: Optional[MediaDownloadType]
    bytes_media: Optional[bytes] = None
    file_id: Optional[str] = None
    collection: Optional[MediaCollection] = None
    original_filename: Optional[str] = None
    downloaded_by: Optional[int] = None
