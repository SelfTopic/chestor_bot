from dataclasses import dataclass


@dataclass(frozen=True)
class MediaInsert:
    media_type: str
    telegram_file_id: str
    collection: str
    path: str
    uploaded_by: int
