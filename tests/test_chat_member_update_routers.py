"""routers/chat_member_update_routers: бот добавлен в чат, участник вошёл/вышел.
Приветствие/прощание отправляются только если заданы для чата; если апдейт о входе
пришёл раньше любого обычного сообщения в этом чате, Chat ещё нет в БД —
ChatNotFoundInDatabase уходит в on_error, как у прода. Вход и выход ведут учёт участников
чата (ChatParticipant), сообщения в группе считает SyncEntitiesMiddleware."""

from typing import Any

import pytest
from sqlalchemy import select, update

from src.bot.dialogs import Dialogs
from src.bot.exceptions import ChatNotFoundInDatabase
from src.database.models import Chat, ChatParticipant, User

from .conftest import (
    chat_member_update,
    message_update,
    owner_dict,
    phrase_texts,
    user_dict,
)

GROUP = -100777


async def _seed_chat(feed, telegram, uid: int = 42) -> None:
    """Первое обычное сообщение в группе заводит Chat через SyncEntitiesMiddleware."""
    telegram.results["getChatAdministrators"] = [owner_dict(99)]
    await feed(message_update("любой текст", uid=uid, chat=GROUP))
    telegram.calls.clear()


class TestBotAdded:
    async def test_replies_when_bot_is_added(self, feed):
        telegram = await feed(
            chat_member_update(1, GROUP, "left", "member", my_chat_member=True)
        )

        (sent,) = telegram.sent
        assert sent in phrase_texts(Dialogs.moderation.bot_added())

    async def test_bot_leave_transition_has_no_handler(self, feed):
        # прод держит тут пустой TODO-хендлер (см. left_chat_member.py); порт его не
        # завёл вовсе, так что апдейт просто ни на что не отвечает
        telegram = await feed(
            chat_member_update(1, GROUP, "member", "left", my_chat_member=True)
        )

        assert telegram.sent == []


class TestNewChatMember:
    async def test_no_chat_in_database_goes_to_on_error(self, feed, dispatcher):
        # ChatMemberUpdated — не Message, Dispatcher.on_error отвечает в чат только
        # на Message, поэтому тут молчание, а не global_error текст; ошибка всё
        # равно долетает до on_error (см. EXPECTED_ERRORS/dispatcher fixture)
        telegram = await feed(chat_member_update(42, GROUP, "left", "member"))

        assert telegram.sent == []
        assert isinstance(dispatcher.errors[-1], ChatNotFoundInDatabase)

    async def test_no_welcome_message_is_silent(self, feed, telegram):
        await _seed_chat(feed, telegram)

        replies = await feed(chat_member_update(43, GROUP, "left", "member"))

        assert replies.sent == []

    async def test_welcome_message_is_sent(self, feed, telegram, session_factory):
        await _seed_chat(feed, telegram)

        async with session_factory() as session:
            await session.execute(
                update(Chat)
                .where(Chat.telegram_id == GROUP)
                .values(welcome_message="Привет!")
            )
            await session.commit()

        replies = await feed(chat_member_update(43, GROUP, "left", "member"))

        assert replies.sent == ["Привет!"]


class TestLeftChatMember:
    async def test_no_chat_in_database_goes_to_on_error(self, feed, dispatcher):
        telegram = await feed(chat_member_update(42, GROUP, "member", "left"))

        assert telegram.sent == []
        assert isinstance(dispatcher.errors[-1], ChatNotFoundInDatabase)

    async def test_no_goodbye_message_is_silent(self, feed, telegram):
        await _seed_chat(feed, telegram)

        replies = await feed(chat_member_update(43, GROUP, "member", "left"))

        assert replies.sent == []

    async def test_goodbye_message_is_sent(self, feed, telegram, session_factory):
        await _seed_chat(feed, telegram)

        async with session_factory() as session:
            await session.execute(
                update(Chat)
                .where(Chat.telegram_id == GROUP)
                .values(goodbye_message="Пока!")
            )
            await session.commit()

        replies = await feed(chat_member_update(43, GROUP, "member", "left"))

        assert replies.sent == ["Пока!"]


async def participant(session_factory, telegram_id: int) -> ChatParticipant | None:
    async with session_factory() as session:
        return await session.get(
            ChatParticipant, {"chat_id": GROUP, "telegram_id": telegram_id}
        )


class TestParticipants:
    async def test_group_messages_are_counted(self, feed, telegram, session_factory):
        await _seed_chat(feed, telegram)
        await feed(message_update("ещё", uid=42, chat=GROUP))

        row = await participant(session_factory, 42)
        assert row is not None and row.messages_total == 2

    async def test_private_messages_are_not(self, send, session_factory):
        await send("привет", uid=42)

        async with session_factory() as session:
            assert (await session.scalars(select(ChatParticipant))).all() == []

    @pytest.mark.parametrize(
        ("extra", "method"),
        [
            ({}, "self"),
            ({"from": user_dict(99, "Админ")}, "added_by_admin"),
            ({"invite_link": "link"}, "invite_link"),
            ({"via_join_request": True}, "join_request"),
            ({"invite_link": "link", "via_chat_folder_invite_link": True}, "chat_folder_invite_link"),
        ],
    )
    async def test_join_is_recorded_with_method(
        self, feed, telegram, session_factory, extra: dict[str, Any], method: str
    ):
        await _seed_chat(feed, telegram)
        update = chat_member_update(43, GROUP, "left", "member", first_name="Петя")
        if extra.get("invite_link") == "link":
            extra = {**extra, "invite_link": invite_link_dict()}
        update["chat_member"].update(extra)

        await feed(update)

        row = await participant(session_factory, 43)
        assert row is not None
        assert row.join_method == method
        assert row.joined_at is not None
        assert row.messages_total == 0
        async with session_factory() as session:
            user = await session.scalar(select(User).where(User.telegram_id == 43))
            assert user is not None and user.first_name == "Петя"

    async def test_bot_joining_is_not_recorded(self, feed, telegram, session_factory):
        await _seed_chat(feed, telegram)
        update = chat_member_update(43, GROUP, "left", "member")
        update["chat_member"]["new_chat_member"]["user"]["is_bot"] = True

        await feed(update)

        assert await participant(session_factory, 43) is None

    async def test_leaving_removes_the_row(self, feed, telegram, session_factory):
        await _seed_chat(feed, telegram)

        await feed(chat_member_update(42, GROUP, "member", "left"))

        assert await participant(session_factory, 42) is None


def invite_link_dict() -> dict[str, Any]:
    return {
        "invite_link": "https://t.me/+abc",
        "creator": user_dict(99, "Админ"),
        "creates_join_request": False,
        "is_primary": False,
        "is_revoked": False,
    }
