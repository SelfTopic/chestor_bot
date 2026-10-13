"""ModerationTicker: объявляет окончание мута и бана по сроку и сгоревшие варны — в чат
(с упоминанием) и в чат админов. Каждое окончание — один раз; перекрытое более поздним
действием (размут, новый мут, разбан, кик) не объявляется."""

from datetime import timedelta

import pytest
from sqlalchemy import update

from src.bot.dialogs import Dialogs
from src.bot.repositories import ModerationRepository
from src.bot.services.dialog import DialogService
from src.bot.services.moderation import ModerationTicker
from src.bot.types import ModerationActionType
from src.bot.utils import utcnow_naive
from src.database.models import ModerationAction, ModerationWarning

from .conftest import phrase_texts
from .test_common_routers import seed
from .test_moderation import ADMIN, ADMIN_CHAT, GROUP, TARGET, set_settings
from .test_notification_ticker import FakeNotifier

neutral = Dialogs.moderation.neutral
MENTION = f'<a href="tg://user?id={TARGET}">Петя</a>'


@pytest.fixture
async def ticker(session_factory) -> tuple[ModerationTicker, FakeNotifier]:
    await seed(session_factory, TARGET, "Петя")
    await set_settings(session_factory, admin_chat_id=ADMIN_CHAT)
    notifier = FakeNotifier()
    return ModerationTicker(session_factory, notifier, DialogService()), notifier


async def punish(session_factory, action: ModerationActionType, seconds: int | None = 60):
    async with session_factory() as session:
        await ModerationRepository(session).insert_action(
            GROUP, ADMIN, TARGET, action, duration_seconds=seconds, reason=None
        )
        await session.commit()


async def warn(session_factory, count: int = 1):
    async with session_factory() as session:
        for _ in range(count):
            await ModerationRepository(session).add_warning(GROUP, ADMIN, TARGET, None, 60)
        await session.commit()


async def expire(session_factory, model, limit: int | None = None):
    past = utcnow_naive() - timedelta(minutes=1)
    async with session_factory() as session:
        stmt = update(model).values(expires_at=past).where(model.expires_at.is_not(None))
        if limit is not None:
            stmt = stmt.where(model.id <= limit)
        await session.execute(stmt)
        await session.commit()


def texts_to(notifier: FakeNotifier, chat_id: int) -> list[str]:
    return [text for target, text in notifier.messages if target == chat_id]


async def test_expired_mute_is_announced_once(session_factory, ticker):
    ticker_, notifier = ticker
    await punish(session_factory, ModerationActionType.MUTE)
    await ticker_.tick()
    assert notifier.messages == []  # срок ещё не вышел

    await expire(session_factory, ModerationAction)
    await ticker_.tick()
    await ticker_.tick()

    (in_chat,) = texts_to(notifier, GROUP)
    assert in_chat in phrase_texts(neutral.mute_expired(name=MENTION))
    (logged,) = texts_to(notifier, ADMIN_CHAT)
    assert logged in phrase_texts(
        neutral.log_mute_expired(chat="группа", name="Петя", id=TARGET)
    )


async def test_expired_ban_goes_only_to_the_admin_chat(session_factory, ticker):
    ticker_, notifier = ticker
    await punish(session_factory, ModerationActionType.BAN)
    await expire(session_factory, ModerationAction)

    await ticker_.tick()

    assert texts_to(notifier, GROUP) == []
    (logged,) = texts_to(notifier, ADMIN_CHAT)
    assert logged in phrase_texts(
        neutral.log_ban_expired(chat="группа", name="Петя", id=TARGET)
    )


@pytest.mark.parametrize(
    ("punishment", "later"),
    [
        (ModerationActionType.MUTE, ModerationActionType.UNMUTE),
        (ModerationActionType.MUTE, ModerationActionType.MUTE),
        (ModerationActionType.BAN, ModerationActionType.KICK),
    ],
)
async def test_superseded_punishment_is_not_announced(
    session_factory, ticker, punishment, later
):
    ticker_, notifier = ticker
    await punish(session_factory, punishment)
    await punish(session_factory, later, seconds=None)
    await expire(session_factory, ModerationAction, limit=1)

    await ticker_.tick()

    assert notifier.messages == []


async def test_expired_warnings_are_announced_once_per_member(session_factory, ticker):
    ticker_, notifier = ticker
    await warn(session_factory, count=3)
    await expire(session_factory, ModerationWarning, limit=2)

    await ticker_.tick()
    await ticker_.tick()

    (in_chat,) = texts_to(notifier, GROUP)
    assert in_chat in phrase_texts(neutral.warn_expired(name=MENTION, count=1, limit=3))
    (logged,) = texts_to(notifier, ADMIN_CHAT)
    assert logged in phrase_texts(
        neutral.log_warn_expired(chat="группа", name="Петя", id=TARGET, count=1, limit=3)
    )


async def test_disabled_notices_are_not_sent(session_factory, ticker):
    ticker_, notifier = ticker
    await set_settings(session_factory, notices_enabled=False)
    await punish(session_factory, ModerationActionType.MUTE)
    await expire(session_factory, ModerationAction)

    await ticker_.tick()

    assert notifier.messages == []

