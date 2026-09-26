from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select, update

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.chat_participant import ChatParticipantRepository
from src.bot.types.insert import ChatInsert
from src.bot.utils import utcnow_naive
from src.database.models import ChatParticipant


@pytest.fixture
def chat_repo(session):
    return ChatRepository(session)


@pytest.fixture
def chat_participant_repo(session):
    return ChatParticipantRepository(session)


@pytest.fixture
def make_chat(chat_repo):
    async def _make(telegram_id: int = 900_000_001):
        return await chat_repo.upsert(
            ChatInsert(
                telegram_id=telegram_id, title="Test chat", username=None, creator_id=None
            )
        )

    return _make


async def _backdate_last_seen(session, chat_id: int, telegram_id: int, when: datetime) -> None:
    """Тестовый хелпер - подделывает `last_seen_at` в прошлое, чтобы
    проверить ленивый сброс календарных счётчиков без реального ожидания."""

    await session.execute(
        update(ChatParticipant)
        .where(
            ChatParticipant.chat_id == chat_id, ChatParticipant.telegram_id == telegram_id
        )
        .values(last_seen_at=when)
    )


async def _get_row(session, chat_id: int, telegram_id: int) -> ChatParticipant:
    row = await session.get(ChatParticipant, {"chat_id": chat_id, "telegram_id": telegram_id})
    assert row is not None
    return row


# --- record_message / random_participant -------------------------------------


async def test_random_participant_only_picks_from_that_chat(
    chat_participant_repo, make_chat, make_user
):
    """Регрессия: два чата с разными участниками не должны смешиваться -
    случайный выбор в чате A никогда не должен вернуть участника чата B."""

    await make_chat(telegram_id=900_000_003)
    await make_chat(telegram_id=900_000_004)
    await make_user(telegram_id=700_000_003, username="tw_700003")
    await make_user(telegram_id=700_000_004, username="tw_700004")

    await chat_participant_repo.record_message(chat_id=900_000_003, telegram_id=700_000_003)
    await chat_participant_repo.record_message(chat_id=900_000_004, telegram_id=700_000_004)

    for _ in range(10):
        result = await chat_participant_repo.random_participant(900_000_003)
        assert result is not None
        assert result.telegram_id == 700_000_003


async def test_record_message_is_idempotent_for_same_pair(
    chat_participant_repo, make_chat, make_user, session
):
    """ON CONFLICT DO UPDATE - повторный вызов для той же пары (chat_id,
    telegram_id) не должен падать/дублировать строку."""

    await make_chat(telegram_id=900_000_005)
    await make_user(telegram_id=700_000_005)

    await chat_participant_repo.record_message(chat_id=900_000_005, telegram_id=700_000_005)
    await chat_participant_repo.record_message(chat_id=900_000_005, telegram_id=700_000_005)

    count = await session.scalar(
        select(func.count()).select_from(ChatParticipant).where(
            ChatParticipant.chat_id == 900_000_005
        )
    )
    assert count == 1


# --- record_message - счётчики и календарный сброс ---------------------------


async def test_record_message_first_time_sets_all_counters_to_one(
    chat_participant_repo, make_chat, make_user, session
):
    await make_chat(telegram_id=900_000_010)
    await make_user(telegram_id=700_000_010)

    await chat_participant_repo.record_message(chat_id=900_000_010, telegram_id=700_000_010)

    row = await _get_row(session, 900_000_010, 700_000_010)
    assert (row.messages_total, row.messages_today, row.messages_week, row.messages_month) == (
        1,
        1,
        1,
        1,
    )


async def test_record_message_within_same_day_increments_all_counters(
    chat_participant_repo, make_chat, make_user, session
):
    await make_chat(telegram_id=900_000_011)
    await make_user(telegram_id=700_000_011)

    await chat_participant_repo.record_message(chat_id=900_000_011, telegram_id=700_000_011)
    await chat_participant_repo.record_message(chat_id=900_000_011, telegram_id=700_000_011)
    await chat_participant_repo.record_message(chat_id=900_000_011, telegram_id=700_000_011)

    row = await _get_row(session, 900_000_011, 700_000_011)
    assert (row.messages_total, row.messages_today, row.messages_week, row.messages_month) == (
        3,
        3,
        3,
        3,
    )


async def test_record_message_next_day_resets_only_daily_counter(
    chat_participant_repo, make_chat, make_user, session
):
    await make_chat(telegram_id=900_000_012)
    await make_user(telegram_id=700_000_012)

    await chat_participant_repo.record_message(chat_id=900_000_012, telegram_id=700_000_012)
    await chat_participant_repo.record_message(chat_id=900_000_012, telegram_id=700_000_012)

    # Откатываем last_seen_at на вчера (та же неделя/месяц, если тест не
    # запущен ровно в понедельник/1-е число - крайне маловероятно, но
    # честно: если запущен, week/month тоже честно сбросятся, это не
    # ломает проверку day-сброса ниже).
    await _backdate_last_seen(
        session, 900_000_012, 700_000_012, utcnow_naive() - timedelta(days=1)
    )

    await chat_participant_repo.record_message(chat_id=900_000_012, telegram_id=700_000_012)

    row = await _get_row(session, 900_000_012, 700_000_012)
    assert row.messages_today == 1
    assert row.messages_total == 3


async def test_record_message_next_month_resets_month_but_keeps_total(
    chat_participant_repo, make_chat, make_user, session
):
    await make_chat(telegram_id=900_000_013)
    await make_user(telegram_id=700_000_013)

    await chat_participant_repo.record_message(chat_id=900_000_013, telegram_id=700_000_013)
    await chat_participant_repo.record_message(chat_id=900_000_013, telegram_id=700_000_013)

    await _backdate_last_seen(
        session, 900_000_013, 700_000_013, utcnow_naive() - timedelta(days=40)
    )

    await chat_participant_repo.record_message(chat_id=900_000_013, telegram_id=700_000_013)

    row = await _get_row(session, 900_000_013, 700_000_013)
    assert row.messages_month == 1
    assert row.messages_week == 1
    assert row.messages_today == 1
    assert row.messages_total == 3


# --- record_join --------------------------------------------------------------


async def test_record_join_does_not_reset_existing_message_counters(
    chat_participant_repo, make_chat, make_user, session
):
    """Порядок "сначала написал, потом событие входа поймали" - редкий, но
    возможный (например бот пропустил апдейт) - join не должен обнулить
    уже накопленную статистику сообщений."""

    await make_chat(telegram_id=900_000_021)
    await make_user(telegram_id=700_000_021)

    await chat_participant_repo.record_message(chat_id=900_000_021, telegram_id=700_000_021)
    await chat_participant_repo.record_message(chat_id=900_000_021, telegram_id=700_000_021)

    await chat_participant_repo.record_join(
        chat_id=900_000_021,
        telegram_id=700_000_021,
        joined_at=datetime(2026, 1, 1),
        join_method="self",
    )

    row = await _get_row(session, 900_000_021, 700_000_021)
    assert row.messages_total == 2
    assert row.join_method == "self"
