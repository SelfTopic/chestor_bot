from src.bot.dialogs import PLACEHOLDERS
from src.bot.types import ModerationVoice


def voice_phrases(voice: ModerationVoice) -> dict[str, frozenset[str]]:
    prefix = f"moderation.{voice.value}."
    return {
        key.removeprefix(prefix): names
        for key, names in PLACEHOLDERS.items()
        if key.startswith(prefix)
    }


def test_every_voice_has_the_same_phrases():
    neutral = voice_phrases(ModerationVoice.NEUTRAL)

    assert neutral
    for voice in ModerationVoice:
        assert voice_phrases(voice) == neutral, voice
