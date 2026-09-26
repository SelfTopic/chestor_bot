"""Мидлвари уровня апдейта: Database, SyncEntities, Ban (Logging берётся из библиотеки)."""

from datetime import datetime, timedelta, timezone

from selfrot import MessageHandler
from selfrot.filter import Text
from selfrot.types import TextMessage
from sqlalchemy import select

from src.bot.repositories import UserRepository
from src.database.models import Chat, User
from src.bot.__main__ import Dispatcher
from src.bot.context import AppContext

from .conftest import admin_dict, callback_update, message_update, owner_dict


async def get_user(session_factory, telegram_id: int) -> User | None:
    async with session_factory() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def ban(session_factory, telegram_id: int, until: datetime | None = None) -> None:
    async with session_factory() as session:
        repo = UserRepository(session)
        await repo.upsert(telegram_id=telegram_id, first_name="Вася")
        await repo.ban(telegram_id, reason="спам", banned_until=until)
        await session.commit()


class TestSyncEntities:
    async def test_creates_user_from_private_message(self, send, session_factory):
        await send("привет", uid=42, first_name="Вася")

        user = await get_user(session_factory, 42)
        assert user is not None
        assert user.first_name == "Вася"
        assert user.has_private_chat is True

    async def test_updates_changed_name(self, send, session_factory):
        await send("привет", uid=42, first_name="Вася")
        await send("привет", uid=42, first_name="Василий")

        user = await get_user(session_factory, 42)
        assert user is not None and user.first_name == "Василий"

    async def test_private_chat_is_not_asked_for_administrators(self, send, telegram):
        await send("привет", uid=42)

        assert telegram.bodies("getChatAdministrators") == []

    async def test_group_message_creates_chat_with_owner_as_creator(
        self, send, telegram, session_factory
    ):
        # владелец не первый в списке: берётся именно он, а не administrators[0]
        telegram.results["getChatAdministrators"] = [admin_dict(5), owner_dict(99)]

        await send("привет", uid=42, chat=-100123)

        async with session_factory() as session:
            chat = await session.scalar(select(Chat).where(Chat.telegram_id == -100123))
        assert chat is not None
        assert chat.title == "группа"
        assert chat.creator_id == 99
        # в группе пользователь появляется, но личка с ботом не подтверждена
        user = await get_user(session_factory, 42)
        assert user is not None and user.has_private_chat is False

    async def test_callback_creates_user_without_asking_administrators(
        self, feed, telegram, session_factory
    ):
        await feed(callback_update("x", uid=43))

        assert await get_user(session_factory, 43) is not None
        assert telegram.bodies("getChatAdministrators") == []


class TestBan:
    async def test_permanent_ban_blocks_handler(self, send, session_factory):
        await ban(session_factory, 42)

        assert await send("бот", uid=42) == []

    async def test_temporary_ban_blocks_and_shows_deadline(self, feed, session_factory):
        future = datetime.now(timezone.utc) + timedelta(days=1)
        await ban(session_factory, 42, until=future)

        assert (await feed(message_update("бот", uid=42))).sent == []

        telegram = await feed(callback_update("x", uid=42))
        (answer,) = telegram.bodies("answerCallbackQuery")
        assert "до " in answer["text"] and "UTC" in answer["text"]

    async def test_other_users_are_not_blocked(self, send, session_factory):
        await ban(session_factory, 42)

        assert len(await send("бот", uid=7)) == 1

    async def test_banned_callback_gets_alert(self, feed, session_factory):
        await ban(session_factory, 42)

        telegram = await feed(callback_update("x", uid=42))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["show_alert"] is True
        assert "заблокированы" in answer["text"] and "спам" in answer["text"]

    async def test_expired_ban_is_lifted_and_committed(self, send, session_factory):
        # unban идёт через сессию DatabaseMiddleware (ContextVar виден в BanMiddleware)
        # и должен закоммититься после хендлера
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        await ban(session_factory, 42, until=past)

        assert len(await send("бот", uid=42)) == 1

        user = await get_user(session_factory, 42)
        assert user is not None and user.is_banned is False


class Boom(MessageHandler[AppContext[TextMessage]]):
    query = Text("boom")

    async def handle(self) -> None:
        await self.ctx.container.user_repository().change_data(
            42, first_name="изменено"
        )
        raise RuntimeError("boom")


class BoomDispatcher(Dispatcher):
    handlers = (Boom,)


class TestDatabaseMiddleware:
    async def test_rolls_back_when_handler_fails(self, feed, telegram, session_factory):
        dp = BoomDispatcher(token="1:TEST", session_factory=session_factory)

        await feed(message_update("привет", uid=42, first_name="Вася"), dp)
        await feed(message_update("boom", uid=42, first_name="Вася"), dp)

        user = await get_user(session_factory, 42)
        assert user is not None and user.first_name == "Вася"

        await dp.api.close_session()
