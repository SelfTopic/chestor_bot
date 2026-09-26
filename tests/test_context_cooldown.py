"""AppContext.cooldown_remaining: общий хелпер для проверки кулдауна, рассчитанный
на переиспользование в любом будущем роутере (не только ghoul_routers). Снимает
только идентичную у всех пяти прод-мест часть (get_active_cooldown + parse_seconds
от end_at - time.time()) — текст ответа и ключ dialogs.json остаются на хендлере,
потому что у прода они не унифицированы (см. context.py)."""

from selfrot import MessageHandler
from selfrot.filter import HasUser, Text

from src.bot.repositories.user_coldown import UserCooldownRepository
from src.database.models import Cooldown
from src.bot.__main__ import Dispatcher
from src.bot.context import AppContext
from src.bot.routers.types import TextUserMessage

from .conftest import message_update
from .test_common_routers import seed


class CooldownCheckHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("кулдаун", ignore_case=True) & HasUser()

    async def handle(self) -> None:
        remaining = await self.ctx.cooldown_remaining(self.ctx.message.user.id, "SNAP")
        if remaining is None:
            await self.ctx.message.answer("свободен")
            return

        await self.ctx.message.answer(
            f"{remaining.minutes_remaining}м {remaining.seconds_remaining}с"
        )


class CooldownDispatcher(Dispatcher):
    handlers = (CooldownCheckHandler,)


async def seed_cooldown(
    session_factory, telegram_id: int, name: str = "SNAP", duration: int = 60
) -> None:
    async with session_factory() as session:
        session.add(Cooldown(name=name, duration=duration))
        await session.flush()
        await UserCooldownRepository(session).set_cooldown(telegram_id, name)
        await session.commit()


class TestCooldownRemaining:
    async def test_none_when_no_cooldown_registered(self, feed, session_factory):
        dp = CooldownDispatcher(token="1:TEST", session_factory=session_factory)

        telegram = await feed(message_update("кулдаун", uid=42), dp)
        await dp.api.close_session()

        assert telegram.sent == ["свободен"]

    async def test_none_when_cooldown_expired(self, feed, session_factory):
        await seed(session_factory, 42, "Вася")
        await seed_cooldown(session_factory, 42, duration=-60)  # уже истёк
        dp = CooldownDispatcher(token="1:TEST", session_factory=session_factory)

        telegram = await feed(message_update("кулдаун", uid=42), dp)
        await dp.api.close_session()

        assert telegram.sent == ["свободен"]

    async def test_remaining_time_when_active(self, feed, session_factory):
        await seed(session_factory, 42, "Вася")
        await seed_cooldown(session_factory, 42, duration=125)
        dp = CooldownDispatcher(token="1:TEST", session_factory=session_factory)

        telegram = await feed(message_update("кулдаун", uid=42), dp)
        await dp.api.close_session()

        (reply,) = telegram.sent
        assert reply.endswith("с") and "м" in reply
        assert reply != "свободен"

    async def test_different_cooldown_name_does_not_interfere(
        self, feed, session_factory
    ):
        # активный кулдаун другого типа ("KAGUNE_UPGRADE") не должен блокировать
        # проверку "SNAP" — get_active_cooldown ищет по имени, не по факту "есть ли
        # хоть какой-то кулдаун у пользователя"
        await seed(session_factory, 42, "Вася")
        await seed_cooldown(session_factory, 42, name="KAGUNE_UPGRADE", duration=60)
        dp = CooldownDispatcher(token="1:TEST", session_factory=session_factory)

        telegram = await feed(message_update("кулдаун", uid=42), dp)
        await dp.api.close_session()

        assert telegram.sent == ["свободен"]
