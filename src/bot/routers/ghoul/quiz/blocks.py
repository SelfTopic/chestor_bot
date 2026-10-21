from ghoul_quiz import Media
from selfrot.types import (
    InputMediaPhoto,
    InputMediaVideo,
    InputRichBlock,
    InputRichBlockParagraph,
    InputRichBlockPhoto,
    InputRichBlockSectionHeading,
    InputRichBlockVideo,
    Message,
    RichBlockParagraph,
    RichBlockPhoto,
    RichBlockSectionHeading,
    RichBlockVideo,
)

from ...rich import paragraph


def heading(text: str) -> InputRichBlockSectionHeading:
    return InputRichBlockSectionHeading(text=text, size=3)


def paragraphs(text: str) -> list[InputRichBlockParagraph]:
    return [paragraph(line) for line in text.split("\n") if line]


def media_block(media: Media) -> InputRichBlock:
    if media.kind == "video":
        return InputRichBlockVideo(video=InputMediaVideo(media=media.url))
    return InputRichBlockPhoto(photo=InputMediaPhoto(media=media.url))


def question_blocks(message: Message) -> list[InputRichBlock]:
    # Результат правит само сообщение с вопросом: его заголовок, текст и медиа берём из него,
    # картинка и видео возвращаются по file_id, ссылки Telegram не отдаёт.
    blocks: list[InputRichBlock] = []
    if message.rich_message is None:
        return blocks

    for block in message.rich_message.blocks:
        if isinstance(block, RichBlockSectionHeading):
            blocks.append(InputRichBlockSectionHeading(text=block.text, size=block.size))
        elif isinstance(block, RichBlockParagraph):
            blocks.append(InputRichBlockParagraph(text=block.text))
        elif isinstance(block, RichBlockPhoto) and block.photo:
            blocks.append(InputRichBlockPhoto(photo=InputMediaPhoto(media=block.photo[-1].file_id)))
        elif isinstance(block, RichBlockVideo):
            blocks.append(InputRichBlockVideo(video=InputMediaVideo(media=block.video.file_id)))
    return blocks
