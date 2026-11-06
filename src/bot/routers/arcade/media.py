from selfrot.types import (
    InputFile,
    InputMediaAnimation,
    InputMediaPhoto,
    InputRichBlockAnimation,
    InputRichBlockPhoto,
    Message,
    RichBlockAnimation,
)

from src.bot.services.arcade.media import Media, Picture, StoredPicture, StoredVideo, VideoFile


def media_block(media: Media) -> InputRichBlockPhoto | InputRichBlockAnimation:
    match media:
        case Picture(png=png):
            return InputRichBlockPhoto(photo=InputMediaPhoto(media=InputFile(png, "picture.png")))
        case VideoFile(path=path):
            return InputRichBlockAnimation(
                animation=InputMediaAnimation(media=InputFile.from_path(path))
            )
        case StoredVideo(file_id=file_id):
            return InputRichBlockAnimation(animation=InputMediaAnimation(media=file_id))
        case StoredPicture(file_id=file_id):
            return InputRichBlockPhoto(photo=InputMediaPhoto(media=file_id))


def stored(media: Media | None) -> bool:
    return isinstance(media, (StoredVideo, StoredPicture))


def animation_file_id(message: Message | None) -> str | None:
    if message is None or message.rich_message is None:
        return None
    for block in message.rich_message.blocks:
        if isinstance(block, RichBlockAnimation):
            return block.animation.file_id
    return None
