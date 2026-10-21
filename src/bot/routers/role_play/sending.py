from selfrot.types import Message

from src.bot.types.rp_commands import TypeRpCommandEnum


async def send_rp(
    message: Message,
    type_command: TypeRpCommandEnum,
    file_id: str | None,
    text: str,
    *,
    quote: bool = False,
) -> None:
    match type_command:
        case TypeRpCommandEnum.TEXT:
            await (message.reply if quote else message.answer)(text)
        case TypeRpCommandEnum.PHOTO if file_id:
            send_photo = message.reply_photo if quote else message.answer_photo
            await send_photo(photo=file_id, caption=text)
        case TypeRpCommandEnum.ANIMATION if file_id:
            send_animation = (
                message.reply_animation if quote else message.answer_animation
            )
            await send_animation(animation=file_id, caption=text)
