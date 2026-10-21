from typing import Annotated, Literal, Optional

from pydantic import BeforeValidator
from selfrot import CommandArgs, MessageHandler
from selfrot.filter import HasUser

from src.bot.dialogs import Line
from src.bot.types import ChatRight, ModerationVoice

from ....context import AppContext
from ...types import TextUserMessage
from ..filters import FromChatAdmin
from ..flow import ModerationFlow, command

VoiceWord = Annotated[
    Literal["грубый", "нейтральный", "rough", "neutral"], BeforeValidator(str.lower)
]

VOICES: dict[str, ModerationVoice] = {
    "грубый": ModerationVoice.ROUGH,
    "rough": ModerationVoice.ROUGH,
    "нейтральный": ModerationVoice.NEUTRAL,
    "neutral": ModerationVoice.NEUTRAL,
}


class VoiceArgs(CommandArgs):
    voice: Optional[VoiceWord] = None


class VoiceHandler(ModerationFlow, MessageHandler[AppContext[TextUserMessage]]):
    right = ChatRight.CHANGE_INFO
    cmd = command("moderation_voice", "стиль модерации", VoiceArgs)
    query = cmd & HasUser() & FromChatAdmin()

    def voiced_usage(self) -> Line:
        return self.phrases.voice_current()

    async def handle(self) -> None:
        word = self.cmd.parse(self.ctx).voice
        if word is None:
            await self.ctx.say(self.voiced_usage(), reply=True)
            return

        await self.check_moderator()
        voice = VOICES[word]
        await self.ctx.moderation_service.set_voice(self.ctx.message.chat.id, voice)
        self.voice = voice
        await self.ctx.say(self.phrases.voice_set(), reply=True)
        self.report(
            self.phrases.log_voice(chat=self.chat_title, moderator=self.moderator_name)
        )
