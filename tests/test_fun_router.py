"""routers/common/fun: «бот/честор выбери|кто|случайный участник|число», «цитата» и
пассивный калькулятор."""

import json

import pytest

from src.bot.dialogs import Dialogs
from src.bot.routers.common.fun import handlers
from src.bot.services.quotes import QuoteService

from .conftest import matches_phrase, message_update, only_text, owner_dict, phrase_texts, texts

GROUP = -100555
TEXTS = texts()


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


def _quote_service(tmp_path, entries: list[dict]) -> QuoteService:
    path = tmp_path / "quotes.json"
    full = [
        {"character_name": "", "text": "", "source": "anime", "season": None, "series": None} | e
        for e in entries
    ]
    path.write_text(json.dumps(full), encoding="utf-8")
    return QuoteService(path)


class TestQuote:
    async def test_known_character_returns_its_quote(self, send, dispatcher, tmp_path):
        dispatcher.quote_service = _quote_service(
            tmp_path, [{"character_name": "Тестовый Персонаж", "text": "тестовая цитата"}]
        )

        (reply,) = await send("цитата персонаж")
        assert reply == only_text(
            Dialogs.fun.quote.result(character="Тестовый Персонаж", text="тестовая цитата")
        )

    async def test_name_spelling_variants_are_merged(self, send, dispatcher, tmp_path):
        dispatcher.quote_service = _quote_service(
            tmp_path,
            [
                {"character_name": "Ризе Камиширо", "text": "цитата А"},
                {"character_name": "Ризэ Камиширо", "text": "цитата Б"},
            ],
        )

        seen = {(await send("цитата ризе"))[0] for _ in range(20)}
        assert seen == {
            only_text(Dialogs.fun.quote.result(character="Ризе Камиширо", text="цитата А")),
            only_text(Dialogs.fun.quote.result(character="Ризэ Камиширо", text="цитата Б")),
        }

    async def test_typo_still_matches(self, send, dispatcher, tmp_path):
        dispatcher.quote_service = _quote_service(
            tmp_path, [{"character_name": "Тестовый Персонаж", "text": "текст"}]
        )

        (reply,) = await send("цитата персонаш")
        assert reply == only_text(
            Dialogs.fun.quote.result(character="Тестовый Персонаж", text="текст")
        )

    async def test_ambiguous_query_pools_every_match(self, send, dispatcher, tmp_path):
        dispatcher.quote_service = _quote_service(
            tmp_path,
            [
                {"character_name": "Иван Мадо", "text": "раз"},
                {"character_name": "Пётр Мадо", "text": "два"},
            ],
        )

        seen = {(await send("цитата мадо"))[0] for _ in range(20)}
        assert seen == {
            only_text(Dialogs.fun.quote.result(character="Иван Мадо", text="раз")),
            only_text(Dialogs.fun.quote.result(character="Пётр Мадо", text="два")),
        }

    async def test_unknown_character(self, send, dispatcher, tmp_path):
        dispatcher.quote_service = _quote_service(tmp_path, [])

        (reply,) = await send("цитата абырвалг")
        assert matches_phrase(reply, "fun.quote.not_found")

    async def test_no_name_picks_fully_random(self, send, dispatcher, tmp_path):
        dispatcher.quote_service = _quote_service(
            tmp_path,
            [
                {"character_name": "Персонаж Один", "text": "раз"},
                {"character_name": "Персонаж Два", "text": "два"},
            ],
        )

        seen = {(await send("цитата"))[0] for _ in range(20)}
        assert seen == {
            only_text(Dialogs.fun.quote.result(character="Персонаж Один", text="раз")),
            only_text(Dialogs.fun.quote.result(character="Персонаж Два", text="два")),
        }
