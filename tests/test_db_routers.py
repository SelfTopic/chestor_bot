"""Роутеры с БД из routers/common: check_balance ("бал") и profile ("профиль", /profile)."""

import pytest

from src.bot.repositories import UserRepository


async def set_user(session_factory, telegram_id: int, **data) -> None:
    async with session_factory() as session:
        repo = UserRepository(session)
        await repo.upsert(telegram_id=telegram_id, first_name="Вася")
        await repo.change_data(telegram_id, **data)
        await session.commit()


class TestBalance:
    @pytest.mark.parametrize("text", ["бал", "Бал", "БАЛ"])
    async def test_shows_balance_and_name(self, send, session_factory, text):
        await set_user(session_factory, 42, balance=123)

        assert await send(text, uid=42) == ["Вася, твой баланс составляет 123 CheSton."]

    async def test_new_user_is_created_by_sync_and_has_zero(self, send):
        # пользователя в БД ещё не было: его создаёт SyncEntitiesMiddleware до хендлера
        assert await send("бал", uid=77, first_name="Новичок") == [
            "Новичок, твой баланс составляет 0 CheSton."
        ]

    @pytest.mark.parametrize("text", ["баланс", "бал ", "мой бал"])
    async def test_ignores_other_text(self, send, text):
        assert await send(text) == []


class TestProfile:
    @pytest.mark.parametrize("text", ["профиль", "Профиль", "/profile", "/profile abc"])
    async def test_shows_profile(self, send, session_factory, text):
        await set_user(session_factory, 42, balance=50, race_bit=1)

        (reply,) = await send(text, uid=42)

        assert "Имя:Вася" in reply
        assert "Раса: Гуль" in reply
        assert "Баланс: 50" in reply

    async def test_command_with_bot_mention(self, send, session_factory, dispatcher):
        await dispatcher.api.load_me()  # username бота нужен для /command@username
        await set_user(session_factory, 42, race_bit=0)

        (reply,) = await send("/profile@dev_bot", uid=42)
        assert "Раса: Человек" in reply

        # чужой бот в группе: команда адресована не нам
        assert await send("/profile@other_bot", uid=42) == []

    async def test_unknown_race_falls_back(self, send, session_factory):
        await set_user(session_factory, 42, race_bit=99)

        (reply,) = await send("профиль", uid=42)

        assert "Раса: Ээээ.. Пока неясно что это такое." in reply

    @pytest.mark.parametrize("text", ["профиль ", "мой профиль", "/profiles"])
    async def test_ignores_other_text(self, send, text):
        assert await send(text) == []
