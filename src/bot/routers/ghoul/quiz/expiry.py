from selfrot import Bot
from selfrot.types import InputRichBlockParagraph, InputRichMessage

from src.bot.dialogs import Dialogs
from src.bot.session_services import SessionServices

from ...utils import quiet_edit


async def expire_overdue_streaks(services: SessionServices, bot: Bot) -> None:
    expired = await services.quiz_streak_service.take_expired()
    # Правки — после коммита: откат не должен оставить в чате «серия прервана» при живой серии.
    await services.session.commit()

    for streak in expired:
        text = await services.language_service.text_for(streak.chat_id)
        lost = text(Dialogs.quiz.streak_broken(streak=streak.streak))
        result = InputRichMessage.model_validate_json(streak.rich)
        blocks = [*(result.blocks or []), InputRichBlockParagraph(text=lost)]
        with quiet_edit("quiz streak"):
            await bot.edit_message_text(
                chat_id=streak.chat_id,
                message_id=streak.message_id,
                rich_message=InputRichMessage(blocks=blocks),
            )
