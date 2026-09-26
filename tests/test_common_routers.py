"""Остальные роутеры routers/common: start, help, tops, правила, депнуть, перевод,
Role-Play, кагуне и расовый профиль, wordle, anime. Ошибки приложения проверяются
через Dispatcher.on_error (замена error_router)."""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path

import pytest
from dependency_injector import providers
from sqlalchemy import update

from src.bot.exceptions import ChatNotFoundInDatabase
from src.bot.repositories import GhoulRepository, UserRepository
from src.bot.services.wikipedia import WikipediaSummary
from src.database.models import Chat
from src.bot.routers.common.anime.guard import cut_guard
from src.bot.routers.common.transfer.flow import TransferPress

from .conftest import (
    button_data,
    callback_update,
    message_update,
    owner_dict,
)
from .test_update_middlewares import get_user

OLD = datetime(2020, 1, 1)  # аккаунт старше 3 дней: иначе переводы недоступны


async def seed(session_factory, telegram_id: int, first_name: str = "Вася", **data):
    """Пользователь в БД до первого сообщения (username и остальное через data)."""
    username = data.pop("username", None)
    async with session_factory() as session:
        repo = UserRepository(session)
        await repo.upsert(
            telegram_id=telegram_id, first_name=first_name, username=username
        )
        if data:
            await repo.change_data(telegram_id, **data)
        await session.commit()


def global_error(dp, exc: Exception) -> str:
    return dp.dialog_service.text(key="global_error", error=str(exc))


class TestStartAndHelp:
    @pytest.mark.parametrize("text", ["/start", "/start payload"])
    async def test_start_greets_by_name(self, send, text):
        (reply,) = await send(text, uid=42, first_name="Вася")

        dp = send.dispatcher
        assert reply == dp.dialog_service.text(key="start", name="Вася")

    async def test_help(self, send):
        (reply,) = await send("/help")

        assert reply == send.dispatcher.dialog_service.text(
            key="help",
            commands_link="https://t.me/CheStorCommands",
            lore_link="Временно отсутствует",
        )

    @pytest.mark.parametrize("text", ["старт", "/starts", "/helper"])
    async def test_ignores_other_text(self, send, text):
        assert await send(text) == []


class TestTops:
    @pytest.fixture(autouse=True)
    async def users(self, session_factory):
        await seed(session_factory, 1, "Альфа", balance=300)
        await seed(session_factory, 2, "Бета", balance=200)
        await seed(session_factory, 3, "Гамма", balance=100)

    async def test_default_top_is_ordered_by_balance(self, send):
        (reply,) = await send("топ бал", uid=50)

        lines = reply.splitlines()
        assert lines[0] == "Топ 20 самых богатих гулий: "
        assert lines[2:5] == [
            "1. Альфа - 300 CheSton",
            "2. Бета - 200 CheSton",
            "3. Гамма - 100 CheSton",
        ]

    async def test_count_limits_the_top(self, send):
        (reply,) = await send("Топ Бал 2", uid=50)

        assert reply.startswith("Топ 2 ")
        assert "Гамма" not in reply and "Бета" in reply

    @pytest.mark.parametrize("text", ["топ бал 0", "топ бал 51", "топ бал abc"])
    async def test_bad_count(self, send, text):
        assert await send(text) == [
            "Топ нужно указывать положительной цифрой в диапазоне 1-50"
        ]

    async def test_text_after_the_count_is_ignored(self, send):
        (reply,) = await send("топ бал 2 пожалуйста", uid=50)

        assert reply.startswith("Топ 2 ")

    async def test_trailing_space_gives_default_top(self, send):
        # у прода падало с IndexError
        (reply,) = await send("топ бал ", uid=50)

        assert reply.startswith("Топ 20 ")

    async def test_other_command_with_same_prefix_is_ignored(self, send):
        assert await send("топ балл") == []


class TestCheckRules:
    async def test_no_chat_in_database_goes_to_on_error(self, send):
        # в личке чата в БД нет: ChatNotFoundInDatabase, ответ даёт Dispatcher.on_error
        (reply,) = await send("правила", uid=42)

        assert reply == global_error(send.dispatcher, ChatNotFoundInDatabase())

    async def test_group_rules(self, send, telegram, session_factory):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]

        (empty,) = await send("Правила", uid=42, chat=-100123)
        assert empty.startswith("В этом чате правила отсутствуют")

        async with session_factory() as session:
            await session.execute(
                update(Chat)
                .where(Chat.telegram_id == -100123)
                .values(rules="Не спамить")
            )
            await session.commit()

        assert await send("правила", uid=42, chat=-100123) == ["Не спамить"]


class TestDep:
    async def test_bad_format(self, send):
        assert await send("депнуть красный") == [
            "❌ Неверный формат команды. Используйте: депнуть <цвет> <ставка>"
        ]

    async def test_unknown_color(self, send):
        (reply,) = await send("депнуть фиолетовый 100")

        assert reply.startswith("Неизвестный цвет 'фиолетовый'")

    async def test_bet_out_of_range(self, send):
        assert await send("депнуть красный 99") == [
            "Сумма ставки должна быть от 100 до 100000"
        ]

    async def test_not_enough_money(self, send):
        assert await send("депнуть красный 100") == [
            "Недостаточно денег для такой ставки"
        ]

    async def test_bet_changes_balance_and_result_arrives_later(
        self, feed, telegram, session_factory
    ):
        await seed(session_factory, 42, balance=1000)
        # гифка длительностью 0 с: итог придёт через duration + 1 = 1 секунду
        telegram.results["sendAnimation"] = {
            "message_id": 101,
            "date": 5,
            "chat": {"id": 42, "type": "private"},
            "animation": {
                "file_id": "A",
                "file_unique_id": "u",
                "width": 1,
                "height": 1,
                "duration": 0,
            },
        }

        await feed(message_update("депнуть красный 100", uid=42))

        user = await get_user(session_factory, 42)
        assert user is not None and user.balance != 1000  # выиграл или проиграл
        assert telegram.bodies("sendAnimation")  # гифка ушла сразу
        assert telegram.sent == []  # а итог ещё нет: он отложен (self.defer)

        # BackgroundTasks.drain при остановке отменяет спящие таймеры, поэтому ждём сами
        await asyncio.sleep(1.5)
        (result,) = telegram.sent
        assert "100" in result  # ставка есть и в тексте выигрыша, и проигрыша

    async def test_upload_failure_is_reported(self, send, telegram, session_factory):
        await seed(session_factory, 42, balance=1000)
        telegram.errors["sendAnimation"] = (400, "Bad Request: wrong file")

        replies = await send("депнуть красный 100", uid=42)

        # при ошибке загрузки гифки (или её отсутствии) пользователь не остаётся без ответа
        assert replies


class TestTransfer:
    @pytest.fixture(autouse=True)
    async def users(self, session_factory):
        await seed(session_factory, 42, "Вася", balance=1000, created_at=OLD)
        await seed(session_factory, 43, "Петя", username="petya")

    async def confirm(self, feed, telegram, uid=42):
        """Нажать «подтвердить» под последним сообщением бота (ответ или правка)."""
        body = (telegram.bodies("editMessageText") or telegram.bodies("sendMessage"))[
            -1
        ]
        await feed(callback_update(button_data(body, "подтвердить"), uid=uid))

    async def test_full_flow_moves_money(self, feed, telegram, session_factory):
        await feed(message_update("/transfer 100", uid=42, reply_to_uid=43))
        (ask,) = telegram.bodies("sendMessage")
        assert ask["text"].startswith("Перевести 100 CheSton's пользователю Петя?")
        assert len(ask["reply_markup"]["inline_keyboard"]) == 4

        await self.confirm(feed, telegram)
        (step2,) = telegram.bodies("editMessageText")
        assert "Последнее подтверждение: перевести 100" in step2["text"]

        await self.confirm(feed, telegram)
        (done,) = telegram.bodies("editMessageText")
        assert done["text"] == "✅ Переведено 100 CheSton's."

        sender = await get_user(session_factory, 42)
        receiver = await get_user(session_factory, 43)
        assert sender is not None and sender.balance == 900
        assert receiver is not None and receiver.balance == 100

    async def test_wrong_button_cancels(self, feed, telegram, session_factory):
        await feed(message_update("перевести 100", uid=42, reply_to_uid=43))
        (ask,) = telegram.bodies("sendMessage")

        await feed(callback_update(button_data(ask, "не подтвердить"), uid=42))
        (edit,) = telegram.bodies("editMessageText")
        assert edit["text"] == "Перевод отменён."

        # состояние сброшено: повторное нажатие «подтвердить» уже ничего не делает
        await feed(callback_update(button_data(ask, "подтвердить"), uid=42))
        assert telegram.bodies("editMessageText") == []

        sender = await get_user(session_factory, 42)
        assert sender is not None and sender.balance == 1000

    async def test_button_without_session_is_ignored(self, feed, telegram):
        await feed(
            callback_update(TransferPress(step=1, action="confirm").pack(), uid=42)
        )

        assert telegram.bodies("editMessageText") == []

    async def test_other_users_cannot_use_the_dialog(self, feed, telegram):
        # состояние привязано к «чат:пользователь»: у чужого нажатия его нет
        await feed(message_update("/transfer 100", uid=42, reply_to_uid=43))
        (ask,) = telegram.bodies("sendMessage")

        await feed(callback_update(button_data(ask, "подтвердить"), uid=43))

        assert telegram.bodies("editMessageText") == []

    async def test_text_after_the_amount_is_ignored(self, send):
        (reply,) = await send(
            "перевести 100 за пиццу", uid=42, reply_to_uid=43, first_name="Вася"
        )

        assert reply.startswith("Перевести 100 CheSton's пользователю Петя?")

    @pytest.mark.parametrize("text", ["податься 100", "перевод 100", "кинутьу 100"])
    async def test_only_exact_command_words_match(self, send, text):
        # у прода Text("подать", startswith=True) цеплял и «податься»
        assert await send(text, uid=42, reply_to_uid=43) == []

    async def test_by_username_without_reply(self, send):
        (reply,) = await send("кинуть @petya 50", uid=42)

        assert reply.startswith("Перевести 50 CheSton's пользователю petya?")

    async def test_unknown_receiver(self, send):
        assert await send("/transfer @nobody 50", uid=42) == [
            "❌ Пользователь не найден: @nobody"
        ]

    @pytest.mark.parametrize("text", ["/transfer", "перевести @petya", "подать x y"])
    async def test_usage_hint(self, send, text):
        (reply,) = await send(text, uid=42)

        assert reply.startswith("Использование:")

    async def test_amount_required_in_reply_mode(self, send):
        (reply,) = await send("/transfer", uid=42, reply_to_uid=43)

        assert reply.startswith("Укажи сумму перевода")

    async def test_self_transfer_rejected(self, send):
        (reply,) = await send("/transfer 10", uid=42, reply_to_uid=42)

        assert reply.startswith("❌")

    async def test_new_account_rejected(self, send, session_factory):
        await seed(session_factory, 44, "Новичок", balance=1000)  # создан только что

        (reply,) = await send("/transfer 10", uid=44, reply_to_uid=43)

        assert "старше 3 дн." in reply

    async def test_insufficient_balance_rejected(self, send):
        (reply,) = await send("/transfer 5000", uid=42, reply_to_uid=43)

        assert reply.startswith("❌")


class TestRolePlay:
    SET = "/set_rp\nпогладить\nпогладила по головке"

    async def test_text_command_lifecycle(self, send, session_factory):
        await seed(session_factory, 43, "Петя", username="petya")

        assert await send(self.SET, uid=42) == [
            "Установлена Role-Play команда погладить с действием погладила по головке"
        ]
        assert await send("/all_rp", uid=42) == [
            "Список всех Role-Play команд чата: \n\n1. погладить - погладила по головке\n"
        ]

        # в ответ на сообщение и по @username
        assert await send("Погладить", uid=42, first_name="Вася", reply_to_uid=43) == [
            "Вася погладила по головке Петя"
        ]
        assert await send("погладить @petya", uid=42, first_name="Вася") == [
            "Вася погладила по головке Петя"
        ]
        # без адресата команда молчит: нет ни ответа, ни @username
        assert await send("погладить", uid=42) == []
        assert await send("погладить нежно", uid=42) == []
        # текст после адресата игнорируется; в ответ на сообщение аргументы не читаются
        assert await send(
            "погладить @petya очень нежно", uid=42, first_name="Вася"
        ) == ["Вася погладила по головке Петя"]
        assert await send(
            "погладить нежно", uid=42, first_name="Вася", reply_to_uid=43
        ) == ["Вася погладила по головке Петя"]

        assert await send("/del_rp погладить", uid=42) == [
            "Role-Play команда погладить удалена"
        ]
        assert await send("/all_rp", uid=42) == [
            "В этом чате нет Role-Play команд. Используйте /set_rp"
        ]
        assert await send("погладить", uid=42, reply_to_uid=43) == []

    async def test_reply_to_a_person_the_bot_has_never_seen(self, send):
        # имя адресата берётся из самого сообщения, БД для ответа не нужна
        await send(self.SET, uid=42)

        assert await send(
            "погладить",
            uid=42,
            first_name="Вася",
            reply_to_uid=999,
            reply_to_name="Незнакомец",
        ) == ["Вася погладила по головке Незнакомец"]

    async def test_unknown_username_goes_to_on_error(self, send):
        await send(self.SET, uid=42)

        (reply,) = await send("погладить @ghost", uid=42)

        assert "ghost" in reply and "не найден" in reply

    @pytest.mark.parametrize("text", ["/set_rp", "/set_rp одно", "/del_rp"])
    async def test_bad_arguments_go_to_on_error(self, send, text):
        (reply,) = await send(text, uid=42)

        assert reply.startswith(
            send.dispatcher.dialog_service.text("global_error", error="")[:5]
        )

    async def test_new_command_on_photo(self, feed, telegram, monkeypatch):
        photo = [
            {"file_id": "SMALL", "file_unique_id": "a", "width": 1, "height": 1},
            {"file_id": "BIG", "file_unique_id": "b", "width": 9, "height": 9},
        ]

        await feed(
            message_update(
                None, uid=42, photo=photo, caption="/set_rp\nобнять\nобнял(а)"
            )
        )

        # медиа админу больше не пересылается (у прода пересылалось в ADMIN_IDS[0])
        assert telegram.bodies("forwardMessage") == []
        (sent,) = telegram.bodies("sendPhoto")
        assert sent["photo"] == "BIG"
        assert (
            sent["caption"]
            == "Установлена Role-Play команда обнять с действием обнял(а)"
        )

        await feed(message_update("обнять", uid=42, first_name="Вася", reply_to_uid=43))
        (again,) = telegram.bodies("sendPhoto")
        assert again["photo"] == "BIG" and again["caption"] == "Вася обнял(а) Петя"

    async def test_new_command_on_animation(self, feed, telegram, monkeypatch):
        gif = {
            "file_id": "GIF",
            "file_unique_id": "g",
            "width": 1,
            "height": 1,
            "duration": 1,
        }

        await feed(
            message_update(
                None, uid=42, animation=gif, caption="/set_rp\nобнять\nобнял(а)"
            )
        )
        (set_ok,) = telegram.bodies("sendAnimation")
        assert set_ok["animation"] == "GIF"
        assert (
            set_ok["caption"]
            == "Установлена Role-Play команда обнять с действием обнял(а)"
        )

        await feed(message_update("обнять", uid=42, first_name="Вася", reply_to_uid=43))
        (used,) = telegram.bodies("sendAnimation")
        assert used["animation"] == "GIF"
        assert used["caption"] == "Вася обнял(а) Петя"

    async def test_photo_with_too_few_words_gets_usage(self, send, feed, telegram):
        photo = [{"file_id": "P", "file_unique_id": "a", "width": 1, "height": 1}]

        await feed(message_update(None, uid=42, photo=photo, caption="/set_rp обнять"))

        assert telegram.sent == ["Используйте\n/set_rp\n<команда>\n<действие>"]

    async def test_photo_with_other_caption_is_ignored(self, feed, telegram):
        photo = [{"file_id": "P", "file_unique_id": "a", "width": 1, "height": 1}]

        await feed(message_update(None, uid=42, photo=photo, caption="просто фото"))

        assert telegram.calls == []


class TestRaceProfile:
    @pytest.mark.parametrize("text", ["кагуне", "/kagune"])
    async def test_kagune_info_is_rich_message(self, send, telegram, text):
        assert await send(text) == []  # это не sendMessage

        (rich,) = telegram.bodies("sendRichMessage")
        assert "Влияние типов кагуне на статы" in json.dumps(rich, ensure_ascii=False)

    async def test_kagune_info_falls_back_to_text(self, send, telegram):
        telegram.errors["sendRichMessage"] = (400, "Bad Request: rich not supported")

        (reply,) = await send("кагуне")

        assert reply == send.dispatcher.dialog_service.text(key="kagune_info")

    @pytest.mark.parametrize("text", ["распрофиль", "/race_profile"])
    async def test_human_gets_plain_profile(self, send, session_factory, text):
        await seed(session_factory, 42, "Вася", balance=77)

        (reply,) = await send(text, uid=42)

        assert "Человек" in reply and "77" in reply

    async def test_ghoul_gets_rich_profile(self, send, telegram, session_factory):
        uid = 700001  # ghoul_service.get ищет по telegram_id только для id > 666000
        await seed(session_factory, uid, "Гуль", race_bit=1)
        async with session_factory() as session:
            await GhoulRepository(session).upsert(telegram_id=uid, kagune_type_bit=1)
            await session.commit()

        assert await send("распрофиль", uid=uid, first_name="Гуль") == []

        (rich,) = telegram.bodies("sendRichMessage")
        assert "Профиль гуля" in json.dumps(rich, ensure_ascii=False)

    async def test_ghoul_profile_falls_back_to_text(
        self, send, telegram, session_factory
    ):
        uid = 700001
        await seed(session_factory, uid, "Гуль", race_bit=1)
        async with session_factory() as session:
            await GhoulRepository(session).upsert(telegram_id=uid, kagune_type_bit=1)
            await session.commit()
        telegram.errors["sendRichMessage"] = (400, "Bad Request: rich not supported")

        (reply,) = await send("распрофиль", uid=uid, first_name="Гуль")

        assert "Гуль" in reply

    async def test_ghoul_without_ghoul_row_goes_to_on_error(
        self, send, session_factory
    ):
        uid = 700002
        await seed(session_factory, uid, "Гуль", race_bit=1)

        (reply,) = await send("распрофиль", uid=uid, first_name="Гуль")

        assert "Ghoul not found in database" in reply
        send.dispatcher.errors.clear()  # ошибка ожидаемая


class FakeWikipedia:
    """Википедия без сети: по умолчанию статьи нет."""

    def __init__(self, summary: WikipediaSummary | None = None) -> None:
        self.summary = summary

    async def get_summary(self, word):
        return self.summary


class TestWordle:
    @pytest.fixture(autouse=True)
    def no_network(self, dispatcher):
        dispatcher.container.wikipedia_service.override(
            providers.Object(FakeWikipedia())
        )

    async def test_start_and_resume(self, feed, telegram):
        await feed(message_update("вордли", uid=42))
        (board,) = telegram.bodies("sendPhoto")
        assert board["photo"] == "<file:wordle.png>"
        assert "Новая игра" in board["caption"]

        await feed(message_update("/wordle", uid=42))
        (again,) = telegram.bodies("sendPhoto")
        assert "незавершённая игра" in again["caption"]

    @pytest.mark.parametrize("text", ["слово", "два слова", "длинноеслово"])
    async def test_ignores_words_without_active_game(self, feed, telegram, text):
        await feed(message_update(text, uid=42))

        assert telegram.calls == []

    async def test_wrong_guess_replaces_board(self, feed, dispatcher, telegram):
        await feed(message_update("вордли", uid=42))
        dispatcher.container.wordle_service()._sessions[
            42
        ].target = "СТЕНА"  # игра хранит слова в верхнем регистре

        await feed(message_update("лодка", uid=42))

        assert telegram.methods_called("deleteMessage") == 2  # доска и слово игрока
        (board,) = telegram.bodies("sendPhoto")
        assert "Попытка 1 из" in board["caption"]

    async def test_guess_from_other_user_is_ignored(self, feed, dispatcher, telegram):
        await feed(message_update("вордли", uid=42))

        await feed(message_update("лодка", uid=43))

        assert telegram.calls == []

    async def test_win_pays_award(self, feed, dispatcher, telegram, session_factory):
        await feed(message_update("вордли", uid=42))
        dispatcher.container.wordle_service()._sessions[42].target = "СТЕНА"

        await feed(message_update("стена", uid=42))

        assert telegram.sent, telegram.calls
        text = telegram.sent[-1]
        assert "Слово <b>СТЕНА</b> угадано" in text

        # награда случайная (WORDLE_CONFIG.award каждый раз новая): сверяем с текстом
        named = re.search(r"Заработано (\d+) CheSton's", text)
        assert named is not None
        user = await get_user(session_factory, 42)
        assert user is not None and user.balance == int(named.group(1)) > 0


class TestWordleFinishLink:
    """Итог партии: слово это гиперссылка на статью, а не голый URL под текстом."""

    ARTICLE = WikipediaSummary(
        extract="Стена — вертикальная конструкция.",
        url="https://ru.wikipedia.org/wiki/Стена",
    )

    @pytest.fixture(autouse=True)
    def wiki(self, dispatcher):
        dispatcher.container.wikipedia_service.override(
            providers.Object(FakeWikipedia(self.ARTICLE))
        )

    async def start(self, feed, dispatcher):
        await feed(message_update("вордли", uid=42))
        dispatcher.container.wordle_service()._sessions[42].target = "СТЕНА"

    async def test_win_links_the_word(self, feed, dispatcher, telegram):
        await self.start(feed, dispatcher)

        await feed(message_update("стена", uid=42))

        text = telegram.sent[-1]
        assert '<a href="https://ru.wikipedia.org/wiki/Стена">СТЕНА</a>' in text
        assert "📖 Стена — вертикальная конструкция." in text
        assert "🔗" not in text
        assert "<b>СТЕНА</b>" not in text  # слово теперь ссылка, а не жирный текст

    async def test_loss_links_the_word(self, feed, dispatcher, telegram):
        await self.start(feed, dispatcher)

        for word in ("лодка", "книга", "ручка", "берег", "город", "место"):
            await feed(message_update(word, uid=42))

        text = telegram.sent[-1]
        assert text.startswith("😔 Не получилось. Загаданное слово: ")
        assert '<a href="https://ru.wikipedia.org/wiki/Стена">СТЕНА</a>' in text
        assert "🔗" not in text

    async def test_url_is_escaped_in_href(self, feed, dispatcher, telegram):
        dispatcher.container.wikipedia_service.override(
            providers.Object(
                FakeWikipedia(
                    WikipediaSummary(extract="x", url='https://e.org/?a=1&b="2"')
                )
            )
        )
        await self.start(feed, dispatcher)

        await feed(message_update("стена", uid=42))

        assert 'href="https://e.org/?a=1&amp;b=&quot;2&quot;"' in telegram.sent[-1]

    async def test_without_article_the_word_stays_bold(
        self, feed, dispatcher, telegram
    ):
        dispatcher.container.wikipedia_service.override(
            providers.Object(FakeWikipedia())
        )
        await self.start(feed, dispatcher)

        await feed(message_update("стена", uid=42))

        text = telegram.sent[-1]
        assert "<b>СТЕНА</b>" in text and "<a " not in text and "📖" not in text


class TestAnime:
    @pytest.fixture
    def episode(self):
        """Файл серии, которого нет в репозитории; создаётся и убирается тестом."""
        folder = Path("src/assets/videos/tokio_ghoul")
        path = folder / "Season_99_Episode_99.mp4"
        created_folder = not folder.exists()
        folder.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake video")
        yield path
        path.unlink(missing_ok=True)
        if created_folder:
            folder.rmdir()

    async def test_usage(self, send):
        (reply,) = await send("/anime")

        assert reply.startswith("Укажи сезон и серию.")

    async def test_unknown_episode(self, send):
        assert await send("/anime 98 98") == ["❌ Видео сезона 98 серии 98 не найдено."]

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("/anime 99 99 18:37", "❌ Неверный формат команды."),
            ("/anime 99 99 xx 18:47", "❌ Неверный начальный таймкод."),
            ("/anime 99 99 18:37 yy", "❌ Неверный конечный таймкод."),
            (
                "/anime 99 99 18:47 18:37",
                "❌ Конечный таймкод должен быть больше начального.",
            ),
        ],
    )
    async def test_bad_fragment_arguments(self, send, episode, text, expected):
        (reply,) = await send(text)

        assert reply.startswith(expected)


class FakeVideoWorker:
    """Без ffmpeg: результат нарезки выдаётся сразу или по команде теста."""

    def __init__(self, manual: bool = False) -> None:
        self.manual = manual
        self.jobs: list = []

    async def enqueue(self, job):
        self.jobs.append(job)
        if not self.manual:
            self.finish(job)

    @staticmethod
    def finish(job):
        output = Path(job.output_file_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"cut")
        job.result.set_result(output)


class TestAnimeCut:
    @pytest.fixture
    def episode(self):
        folder = Path("src/assets/videos/tokio_ghoul")
        path = folder / "Season_99_Episode_99.mp4"
        created_folder = not folder.exists()
        folder.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake video")
        yield path
        path.unlink(missing_ok=True)
        if created_folder:
            folder.rmdir()

    @pytest.fixture(autouse=True)
    def clean_guard(self):
        cut_guard.clear()
        yield
        cut_guard.clear()

    @pytest.fixture
    def worker(self, dispatcher):
        worker = FakeVideoWorker()
        dispatcher.container.video_worker.override(providers.Object(worker))
        return worker

    async def test_fragment_is_sent_as_video(
        self, feed, telegram, episode, worker, settle
    ):
        await feed(message_update("/anime 99 99 00:10 00:20"))
        await settle()

        assert telegram.sent[0].startswith("⏳ Начинаю нарезку видео...")
        assert telegram.methods_called("deleteMessage") == 1  # сообщение о ходе работы
        (video,) = telegram.bodies("sendVideo")
        assert video["caption"] == (
            "Video\n🎬 Сезон 99. Серия 99. Отрывок с 00:10 до 00:20"
        )

    async def test_fragment_as_gif(self, feed, telegram, episode, worker, settle):
        await feed(message_update("/anime 99 99 00:10 00:20 gif"))
        await settle()

        (gif,) = telegram.bodies("sendAnimation")
        assert gif["caption"].startswith("Gif\n🎬 Сезон 99. Серия 99.")

    async def test_whole_episode_is_uploaded(self, feed, telegram, episode, settle):
        await feed(message_update("/anime 99 99"))
        await settle()

        (video,) = telegram.bodies("sendVideo")
        assert video["video"] == "<file:Season_99_Episode_99.mp4>"
        assert video["caption"] == "🎬 Сезон 99. Серия 99"

    async def test_handler_returns_before_the_cut_is_done(
        self, feed, dispatcher, telegram, episode, settle
    ):
        # долгая часть в after_handle: хендлер закрылся (слот и сессия БД свободны),
        # а видео ещё нет. У прода хендлер ждал нарезку внутри себя.
        worker = FakeVideoWorker(manual=True)
        dispatcher.container.video_worker.override(providers.Object(worker))

        await feed(message_update("/anime 99 99 00:10 00:20"))
        await asyncio.sleep(0.2)

        assert telegram.bodies("sendVideo") == []
        (job,) = worker.jobs

        worker.finish(job)
        await settle()
        assert len(telegram.bodies("sendVideo")) == 1

    async def test_second_cut_of_the_same_user_waits(
        self, feed, dispatcher, telegram, episode, settle
    ):
        worker = FakeVideoWorker(manual=True)
        dispatcher.container.video_worker.override(providers.Object(worker))

        await feed(message_update("/anime 99 99 00:10 00:20", uid=42))
        await asyncio.sleep(0.2)
        await feed(message_update("/anime 99 99 00:10 00:30", uid=42))

        assert telegram.sent == [
            "⏳ У тебя уже есть нарезка в процессе. Дождись её завершения."
        ]

        worker.finish(worker.jobs[0])
        await settle()

    async def test_guard_is_released_after_the_cut(
        self, feed, telegram, episode, worker, settle
    ):
        await feed(message_update("/anime 99 99 00:10 00:20", uid=42))
        await settle()
        await feed(message_update("/anime 99 99 00:10 00:20", uid=42))
        await settle()

        assert len(telegram.bodies("sendVideo")) == 1  # вторая нарезка в этом feed

    async def test_expired_guard_does_not_block_forever(self, send, episode):
        cut_guard.occupy(42, seconds=-1)  # срок давно вышел

        replies = await send("/anime 99 99 00:20 00:10", uid=42)

        assert replies == ["❌ Конечный таймкод должен быть больше начального."]

    @pytest.mark.parametrize("text", ["/anime", "/anime x 1", "/anime 1"])
    async def test_usage_for_missing_or_bad_season(self, send, text):
        (reply,) = await send(text)

        assert reply.startswith("Укажи сезон и серию.")


class TestVideoWorkerLifecycle:
    async def test_worker_starts_and_stops_with_dispatcher(self, dispatcher):
        worker = dispatcher.container.video_worker()

        await dispatcher.on_startup()
        assert worker._is_running

        await dispatcher.on_shutdown()
        assert not worker._is_running
