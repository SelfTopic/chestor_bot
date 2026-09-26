"""routers/chat_member_update_routers: бот добавлен в чат, участник вошёл/вышел.
Приветствие/прощание отправляются только если заданы для чата; если апдейт о входе
пришёл раньше любого обычного сообщения в этом чате, Chat ещё нет в БД —
ChatNotFoundInDatabase уходит в on_error, как у прода."""

from sqlalchemy import update

from src.bot.exceptions import ChatNotFoundInDatabase
from src.database.models import Chat

from .conftest import chat_member_update, message_update, owner_dict

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

        assert telegram.sent == [
            "Пиздато конечно, что вы меня добавили. Я тупой даунский бот."
        ]

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
