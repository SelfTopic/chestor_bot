"""routers/common/fun: «бот/честор выбери|кто|случайный участник|число» и пассивный
калькулятор."""

import pytest
from src.bot.routers.common.fun import handlers

from .conftest import message_update, owner_dict

GROUP = -100555
NOBODY = "Пока некого выбирать - в этом чате ещё никто не написал боту."


async def seed_group(feed, telegram, uid: int = 42, first_name: str = "Вася") -> None:
    """Сообщение в группе заводит Chat и участника через SyncEntitiesMiddleware."""
    telegram.results["getChatAdministrators"] = [owner_dict(99)]
    await feed(message_update("привет", uid=uid, first_name=first_name, chat=GROUP))


class TestPick:
    async def test_items_split_by_comma_and_ili(self, send, monkeypatch):
        seen: list[list[str]] = []

        def choice(items: list[str]) -> str:
            seen.append(items)
            return items[-1]

        monkeypatch.setattr(handlers.random, "choice", choice)

        assert await send("бот выбери пицца, суши или бургер") == [
            "🎲 Выбор пал на: бургер"
        ]
        assert seen == [["пицца", "суши", "бургер"]]

    async def test_chestor_and_any_case(self, send):
        (reply,) = await send("Честор ВЫБЕРИ чай ИЛИ кофе")
        assert reply in ("🎲 Выбор пал на: чай", "🎲 Выбор пал на: кофе")

    async def test_needs_two_items(self, send):
        assert await send("бот выбери пицца") == [
            "Нужно минимум 2 варианта: бот выбери пицца или суши или бургер"
        ]

    async def test_too_many_items(self, send):
        items = ", ".join(str(i) for i in range(51))
        assert await send(f"бот выбери {items}") == [
            "Слишком много вариантов (максимум 50)."
        ]

    async def test_too_long_item(self, send):
        assert await send(f"бот выбери чай или {'к' * 201}") == [
            "Один из вариантов слишком длинный."
        ]

    @pytest.mark.parametrize("text", ["выбери чай или кофе", "бот выбери", "бот, выбери чай или кофе"])
    async def test_other_texts_are_ignored(self, send, text):
        assert await send(text) == []


class TestWho:
    async def test_nobody_known_in_chat(self, send):
        assert await send("бот кто платит") == [NOBODY]

    async def test_names_a_participant(self, feed, telegram):
        await seed_group(feed, telegram, first_name="<Вася>")

        telegram = await feed(
            message_update(
                "бот кто сегодня платит за <всех>", uid=42, first_name="<Вася>", chat=GROUP
            )
        )

        (body,) = telegram.bodies("sendMessage")
        assert body["text"] == (
            "По моим расчётам сегодня платит за &lt;всех&gt; "
            '<a href="tg://user?id=42">&lt;Вася&gt; </a>'
        )
        assert body["parse_mode"] == "HTML"


class TestRandomParticipant:
    async def test_names_a_participant(self, feed, telegram):
        await seed_group(feed, telegram)

        telegram = await feed(message_update("честор случайный участник", uid=42, chat=GROUP))

        assert telegram.sent == ['🎲 Выбор пал на <a href="tg://user?id=42">Вася </a>!']

    async def test_nobody_known_in_chat(self, send):
        assert await send("бот случайный участник") == [NOBODY]

    async def test_trailing_words_are_ignored(self, send):
        assert await send("бот случайный участник пожалуйста") == []


class TestNumber:
    async def test_bounds_in_any_order(self, send, monkeypatch):
        calls: list[tuple[int, int]] = []

        def randint(low: int, high: int) -> int:
            calls.append((low, high))
            return 7

        monkeypatch.setattr(handlers.random, "randint", randint)

        assert await send("бот число 10 -3") == ["🎲 7"]
        assert calls == [(-3, 10)]

    @pytest.mark.parametrize("text", ["бот число 1.5 3", "бот число 1", "бот число +1 3"])
    async def test_not_two_integers_is_ignored(self, send, text):
        assert await send(text) == []


class TestCalculator:
    @pytest.mark.parametrize(
        ("text", "result"),
        [("2+2*2", "6"), ("7 / 2", "3.5"), ("6/3", "2"), ("-(2**3)", "-8"), ("-2-2", "-4"), ("1/2", "0.5")],
    )
    async def test_replies_with_bare_result(self, send, text, result):
        assert await send(text) == [result]

    @pytest.mark.parametrize(
        "text",
        [
            "5",
            "-5",
            "+7999",
            "привет",
            "1/0",
            "10.0 ** 400",  # OverflowError у float
            "9**1000 * 9**1000 * 9**1000 * 9**1000 * 9**1000",  # в сообщение не влезет
            "((9**1000)**1000)**1000",  # без проверки размера бот висел бы минутами
        ],
    )
    async def test_everything_else_is_silent(self, send, text):
        assert await send(text) == []
