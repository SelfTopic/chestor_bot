import pytest
from sqlalchemy import select

from src.bot.exceptions import DurationParseError, TermOutOfRange
from src.bot.repositories import ChatRepository, ModerationRepository
from src.bot.services.moderation import ModerationService
from src.bot.types import ModerationActionType, ModerationVoice, Punishment
from src.bot.types.insert import ChatInsert
from src.database.models import ModerationAction, ModerationSettings

CHAT = -100500


@pytest.fixture
async def moderation(session):
    await ChatRepository(session).upsert(
        ChatInsert(telegram_id=CHAT, title="чат", username=None, creator_id=1)
    )
    return ModerationService(ModerationRepository(session))


async def test_new_chat_gets_default_settings(moderation, session):
    settings = await moderation.settings(CHAT)

    assert settings.mute_default_seconds == 30 * 60
    assert settings.ban_default_seconds == 30 * 60
    assert settings.voice is ModerationVoice.NEUTRAL
    assert settings.admin_chat_id is None
    stored = await session.scalars(select(ModerationSettings))
    assert [row.chat_id for row in stored] == [CHAT]


async def test_settings_keep_what_the_chat_changed(moderation, session):
    await moderation.settings(CHAT)
    await moderation.set_voice(CHAT, ModerationVoice.ROUGH)
    await moderation.set_mute_default(CHAT, 60)
    await moderation.set_ban_default(CHAT, None)
    session.expire_all()

    settings = await moderation.settings(CHAT)

    assert settings.voice is ModerationVoice.ROUGH
    assert (settings.mute_default_seconds, settings.ban_default_seconds) == (60, None)


async def test_record_writes_journal(moderation, session):
    await moderation.record(
        CHAT, 1, 2, ModerationActionType.MUTE, duration_seconds=600, reason="флуд"
    )
    await moderation.record(CHAT, 1, 2, ModerationActionType.UNMUTE)

    rows = (
        await session.scalars(select(ModerationAction).order_by(ModerationAction.id))
    ).all()
    assert [
        (r.chat_id, r.moderator_id, r.target_id, r.action, r.duration_seconds, r.reason)
        for r in rows
    ] == [
        (CHAT, 1, 2, ModerationActionType.MUTE, 600, "флуд"),
        (CHAT, 1, 2, ModerationActionType.UNMUTE, None, None),
    ]


DEFAULT = 1800


@pytest.mark.parametrize(
    ("text", "seconds", "reason"),
    [
        ("30м флуд", 1800, "флуд"),
        ("1 час 30 мин спам и\nмат", 5400, "спам и\nмат"),
        ("флуд 30м", DEFAULT, "флуд 30м"),
        ("30 флуд", DEFAULT, "30 флуд"),
        ("", DEFAULT, None),
        ("навсегда за всё", None, "за всё"),
        ("30с", 30, None),
        ("366д", 366 * 24 * 3600, None),
    ],
)
async def test_punishment_takes_longest_leading_term(moderation, text, seconds, reason):
    assert moderation.punishment(text, DEFAULT) == Punishment(seconds, reason)


@pytest.mark.parametrize("text", ["29с", "367д", "0.1с"])
async def test_punishment_outside_telegram_limits(moderation, text):
    with pytest.raises(TermOutOfRange) as caught:
        moderation.punishment(text, DEFAULT)

    assert (caught.value.min_seconds, caught.value.max_seconds) == (30, 366 * 24 * 3600)


async def test_default_term_is_the_whole_text(moderation):
    assert moderation.term("1 час 30 мин") == 5400
    assert moderation.term("навсегда") is None

    with pytest.raises(DurationParseError):
        moderation.term("1ч флуд")
