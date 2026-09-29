import pytest
from sqlalchemy import select, update

from src.bot.repositories import ChatRepository, ModerationRepository
from src.bot.services.moderation import ModerationService
from src.bot.types import ModerationActionType, ModerationVoice
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
    await session.execute(
        update(ModerationSettings).values(
            voice=ModerationVoice.ROUGH, mute_default_seconds=60
        )
    )
    session.expire_all()

    settings = await moderation.settings(CHAT)

    assert settings.voice is ModerationVoice.ROUGH
    assert settings.mute_default_seconds == 60


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
