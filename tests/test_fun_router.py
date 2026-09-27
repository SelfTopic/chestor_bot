"""routers/common/fun: «бот/честор выбери|кто|случайный участник|число» и пассивный
калькулятор."""

import pytest

from src.bot.dialogs import Dialogs, load_texts
from src.bot.routers.common.fun import handlers

from .conftest import matches_phrase, message_update, owner_dict, phrase_texts

GROUP = -100555
TEXTS = load_texts()


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

        (reply,) = await send("бот выбери пицца, суши или бургер")
        assert reply in phrase_texts(Dialogs.fun.pick.result(choice="бургер"))
        assert seen == [["пицца", "суши", "бургер"]]

    async def test_chestor_and_any_case(self, send):
        (reply,) = await send("Честор ВЫБЕРИ чай ИЛИ кофе")
        assert reply in phrase_texts(Dialogs.fun.pick.result(choice="чай")) | phrase_texts(
            Dialogs.fun.pick.result(choice="кофе")
        )

    async def test_needs_two_items(self, send):
        (reply,) = await send("бот выбери пицца")
        assert matches_phrase(reply, "fun.pick.too_few")

    async def test_too_many_items(self, send):
        items = ", ".join(str(i) for i in range(51))
        (reply,) = await send(f"бот выбери {items}")
        assert matches_phrase(reply, "fun.pick.too_many") and "50" in reply

    async def test_too_long_item(self, send):
        (reply,) = await send(f"бот выбери чай или {'к' * 201}")
        assert matches_phrase(reply, "fun.pick.too_long")

    @pytest.mark.parametrize("text", ["выбери чай или кофе", "бот выбери", "бот, выбери чай или кофе"])
    async def test_other_texts_are_ignored(self, send, text):
        assert await send(text) == []


class TestWho:
    async def test_nobody_known_in_chat(self, send):
        (reply,) = await send("бот кто платит")
        assert matches_phrase(reply, "fun.nobody")

    async def test_names_a_participant(self, feed, telegram):
        await seed_group(feed, telegram, first_name="<Вася>")

        telegram = await feed(
            message_update(
                "бот кто сегодня платит за <всех>", uid=42, first_name="<Вася>", chat=GROUP
            )
        )

        (body,) = telegram.bodies("sendMessage")
        assert body["text"] in phrase_texts(
            Dialogs.fun.who(
                question="сегодня платит за &lt;всех&gt;",
                mention='<a href="tg://user?id=42">&lt;Вася&gt; </a>',
            )
        )
        assert body["parse_mode"] == "HTML"


class TestRandomParticipant:
    async def test_names_a_participant(self, feed, telegram):
        await seed_group(feed, telegram)

        telegram = await feed(message_update("честор случайный участник", uid=42, chat=GROUP))

        (sent,) = telegram.sent
        assert sent in phrase_texts(
            Dialogs.fun.random_participant(mention='<a href="tg://user?id=42">Вася </a>')
        )

    async def test_nobody_known_in_chat(self, send):
        (reply,) = await send("бот случайный участник")
        assert matches_phrase(reply, "fun.nobody")

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

    @pytest.mark.parametrize("text", ["5", "-5", "+7999", "привет", "2 + + +"])
    async def test_everything_else_is_silent(self, send, text):
        assert await send(text) == []

    @pytest.mark.parametrize("text", ["1/0", "5 % 0"])
    async def test_division_by_zero_gets_an_easter_egg(self, send, text):
        (reply,) = await send(text)
        assert reply in TEXTS["fun.calculator.division_by_zero"].variants

    @pytest.mark.parametrize(
        "text",
        [
            "10.0 ** 400",
            "9**1000 * 9**1000 * 9**1000 * 9**1000 * 9**1000",  # в сообщение не влезет
            "((9**1000)**1000)**1000",  # без проверки размера бот висел бы минутами
        ],
    )
    async def test_too_big_gets_an_easter_egg(self, send, text):
        (reply,) = await send(text)
        assert reply in TEXTS["fun.calculator.too_big"].variants
