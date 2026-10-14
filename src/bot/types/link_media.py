from dataclasses import dataclass


@dataclass(frozen=True)
class CachedVideo:
    file_id: str


@dataclass(frozen=True)
class CachedSlideshow:
    photo_file_ids: tuple[str, ...]
    audio_file_id: str | None


CachedMedia = CachedVideo | CachedSlideshow
