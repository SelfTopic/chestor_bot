"""routers/ghoul_routers: GhoulMiddleware гейтит весь роутер (без гуля — молчание с
подсказкой, кроме "растить кагуне"; мёртвому гулю тоже отказ). coffee.py: использует
ctx.say (гифка фразы coffee.done из папки coffee; кулдаун — не через
ctx.cooldown_remaining, а CoffeeService.execute_cooldown, который сам решает COFFEE
это или COFFEE_DAY, см. coffee.py). upgrade_kagune/: единственная команда, доступная
и без гуля (регистрация), и мёртвому гулю (возрождение) — bypass в GhoulMiddleware;
типизированный KaguneUpgradePress вместо ручного parse_kagune_callback_payload."""

import json
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update
from ghoul_quiz import (
    Answer,
    Media,
    Question,
    TrueFalseAnswer,
    TrueFalseQuestion,
    WhoisAnswer,
    WhoisQuestion,
)

from src.bot.config import game_config
from src.bot.dialogs import Dialogs
from src.bot.exceptions import QuizModeDisabled
from src.bot.game_configs import QUIZ_CONFIG, STAT_UPGRADE_CONFIG
from src.bot.repositories import GhoulRepository, UserCooldownRepository
from src.bot.routers.ghoul_routers.upgrade_stat import STAT_LABELS
from src.bot.tasks import QuizStreakExpiry
from src.bot.types import KaguneType
from src.bot.utils import (
    calculate_kagune,
    format_amount,
    format_duration,
    get_hunger_tier,
    health_regen_per_hour,
    hours_until_full_health,
)
from src.config import settings
from src.database.models import Cooldown, Ghoul, QuizStreak

from .conftest import (
    button_data,
    callback_update,
    chat_dict,
    matches_phrase,
    member_dict,
    message_update,
    only_text,
    owner_dict,
    phrase_texts,
    rich_texts,
)
from .test_common_routers import seed
from .test_update_middlewares import get_user

# GhoulService.get() трактует telegram_id <= 666000 как внутренний id гуля, не
# telegram_id (известная особенность порта) — тесты гуля всегда выше этого порога.
UID = 700001


async def seed_ghoul(session_factory, telegram_id: int, **fields):
    async with session_factory() as session:
        await GhoulRepository(session).upsert(telegram_id=telegram_id, **fields)
        await session.commit()


async def get_ghoul(session_factory, telegram_id: int) -> Ghoul | None:
    async with session_factory() as session:
        return await GhoulRepository(session).get(telegram_id)


async def seed_cooldown_type(session_factory, name: str, duration: int) -> None:
    async with session_factory() as session:
        session.add(Cooldown(name=name, duration=duration))
        await session.commit()


async def seed_active_cooldown(
    session_factory, telegram_id: int, name: str, duration: int = 1800
) -> None:
    await seed_cooldown_type(session_factory, name, duration)
    async with session_factory() as session:
        await UserCooldownRepository(session).set_cooldown(telegram_id, name)
        await session.commit()


async def balance_of(session_factory, telegram_id: int) -> int:
    user = await get_user(session_factory, telegram_id)
    assert user is not None
    return user.balance


class TestGhoulMiddleware:
    async def test_no_ghoul_is_blocked_with_hint(self, send):
        (reply,) = await send("пить кофе", uid=UID)
        assert matches_phrase(reply, "ghoul.not_a_ghoul")

    async def test_grow_kagune_bypasses_even_without_a_ghoul(self, send):
        # миддлварь не блокирует апдейт хинтом "ты не гуль" — доходит до хендлера
        # регистрации (подробно проверяется в TestUpgradeKagune)
        (reply,) = await send("растить кагуне", uid=UID)
        assert matches_phrase(reply, "ghoul.new")

    async def test_dead_ghoul_is_blocked(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, is_dead=True)

        (reply,) = await send("пить кофе", uid=UID)
        assert matches_phrase(reply, "ghoul.dead")

    async def test_alive_ghoul_reaches_the_handler(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=0)

        # snap_count=0 < COFFEE_CONFIG.snap_limit: до хендлера дошло, просто отказ
        # по другой причине (не хинт "ты не гуль")
        (reply,) = await send("пить кофе", uid=UID)
        assert matches_phrase(reply, "coffee.snap_limit")


CHANNEL = "@chestor_channel"


class TestChannelSubscription:
    @pytest.fixture(autouse=True)
    def channel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "SUBSCRIPTION_CHANNEL", CHANNEL)

    async def test_unsubscribed_player_gets_buttons_instead_of_the_game(self, feed, telegram):
        telegram.results["getChatMember"] = member_dict("left", UID)

        await feed(message_update("пить кофе", uid=UID))

        (asked,) = telegram.bodies("getChatMember")
        assert asked["chat_id"] == CHANNEL
        (body,) = telegram.bodies("sendMessage")
        assert body["text"] in phrase_texts(Dialogs.subscription.required(channel=CHANNEL))
        buttons = [b for row in body["reply_markup"]["inline_keyboard"] for b in row]
        assert buttons[0] == {
            "text": only_text(Dialogs.subscription.subscribe_button()),
            "url": "https://t.me/chestor_channel",
        }
        assert button_data(body, only_text(Dialogs.subscription.check_button()))

    async def test_subscriber_reaches_the_game_and_is_not_asked_again(self, send, telegram):
        telegram.results["getChatMember"] = member_dict("member", UID)

        (reply,) = await send("пить кофе", uid=UID)
        assert matches_phrase(reply, "ghoul.not_a_ghoul")

        await send("пить кофе", uid=UID)
        assert telegram.methods_called("getChatMember") == 0

    async def test_check_button_answers_by_the_current_subscription(self, feed, telegram):
        telegram.results["getChatMember"] = member_dict("left", UID)
        await feed(message_update("пить кофе", uid=UID))
        (body,) = telegram.bodies("sendMessage")
        press = callback_update(button_data(body, only_text(Dialogs.subscription.check_button())), uid=UID)

        await feed(press)
        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] in phrase_texts(Dialogs.subscription.not_yet())

        telegram.results["getChatMember"] = member_dict("member", UID)
        await feed(press)
        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] in phrase_texts(Dialogs.subscription.confirmed())

    async def test_unanswered_check_keeps_the_game_open(self, send, telegram):
        telegram.errors["getChatMember"] = (400, "Bad Request: member list is inaccessible")

        (reply,) = await send("пить кофе", uid=UID)
        assert matches_phrase(reply, "ghoul.not_a_ghoul")


class TestCoffee:
    async def test_below_snap_limit_is_refused(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=0)

        (reply,) = await send("пить кофе", uid=UID)
        assert matches_phrase(reply, "coffee.snap_limit")

    async def test_accepts_without_gif_when_folder_is_empty(
        self, send, session_factory, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=100, coffee_count=0)
        await seed_cooldown_type(session_factory, "COFFEE", duration=1800)

        (reply,) = await send("пить кофе", uid=UID)

        user = await get_user(session_factory, UID)
        assert user is not None
        assert reply in phrase_texts(Dialogs.coffee.done(count=1, money=user.balance))
        assert user is not None and user.balance > 0

    async def test_sends_gif_when_one_exists(
        self, feed, telegram, session_factory, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        folder = tmp_path / "animation" / "coffee"
        folder.mkdir(parents=True)
        (folder / "coffee.mp4").write_bytes(b"gif-bytes")
        telegram.results["sendAnimation"] = {
            "message_id": 1,
            "date": 5,
            "chat": {"id": UID, "type": "private"},
            "animation": {
                "file_id": "NEW_ID",
                "file_unique_id": "u",
                "width": 1,
                "height": 1,
                "duration": 1,
            },
        }
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=100, coffee_count=0)
        await seed_cooldown_type(session_factory, "COFFEE", duration=1800)

        await feed(message_update("пить кофе", uid=UID))

        (body,) = telegram.bodies("sendAnimation")
        assert matches_phrase(body["caption"], "coffee.done")
        assert body["animation"] == "<file:coffee.mp4>"

    async def test_cooldown_reply_then_day_cap_refund_without_double_charge(
        self, send, session_factory, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=100, coffee_count=0)
        await seed_cooldown_type(session_factory, "COFFEE", duration=1800)
        await seed_cooldown_type(session_factory, "COFFEE_DAY", duration=86400)

        (first,) = await send("пить кофе", uid=UID)
        assert matches_phrase(first, "coffee.done")
        balance_after_first = await balance_of(session_factory, UID)

        # повторный клик во время кулдауна COFFEE: рефанд + переход на COFFEE_DAY
        (second,) = await send("пить кофе", uid=UID)
        assert matches_phrase(second, "coffee.cooldown")
        balance_after_second = await balance_of(session_factory, UID)
        assert balance_after_second < balance_after_first

        # третий клик — уже под COFFEE_DAY: тот же ответ, но без повторного рефанда
        (third,) = await send("пить кофе", uid=UID)
        assert matches_phrase(third, "coffee.cooldown")
        balance_after_third = await balance_of(session_factory, UID)
        assert balance_after_third == balance_after_second


class TestUpgradeKagune:
    async def test_creates_ghoul_when_none_exists(self, send, session_factory):
        await seed(session_factory, UID, "Вася")

        (reply,) = await send("растить кагуне", uid=UID)

        assert matches_phrase(reply, "ghoul.new")
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.kagune_type_bit is not None
        kagune_type = calculate_kagune(ghoul.kagune_type_bit)[0]
        assert kagune_type.value["name"] in reply

    async def test_rebirth_when_dead(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(
            session_factory,
            UID,
            is_dead=True,
            kagune_type_bit=KaguneType.UKAKU.value["bit"],
            kagune_strength_ukaku=5,
        )

        (reply,) = await send("растить кагуне", uid=UID)

        assert matches_phrase(reply, "ghoul.reborn")
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None
        assert ghoul.is_dead is False
        assert ghoul.kagune_type_bit is not None

    async def test_cooldown_reply(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(
            session_factory,
            UID,
            kagune_type_bit=KaguneType.UKAKU.value["bit"],
            kagune_strength_ukaku=1,
        )
        await seed_active_cooldown(session_factory, UID, "KAGUNE_UPGRADE")

        (reply,) = await send("растить кагуне", uid=UID)

        assert matches_phrase(reply, "kagune.upgrade.cooldown")

    async def test_single_type_upgrade_succeeds(
        self, send, session_factory, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        await seed(session_factory, UID, "Вася", balance=100000)
        await seed_ghoul(
            session_factory,
            UID,
            kagune_type_bit=KaguneType.UKAKU.value["bit"],
            kagune_strength_ukaku=1,
        )
        await seed_cooldown_type(session_factory, "KAGUNE_UPGRADE", duration=600)

        (reply,) = await send("растить кагуне", uid=UID)

        assert matches_phrase(reply, "kagune.upgrade.done")
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.kagune_strength_ukaku == 2

    async def test_single_type_upgrade_refused_without_money(
        self, send, session_factory
    ):
        await seed(session_factory, UID, "Вася", balance=0)
        await seed_ghoul(
            session_factory,
            UID,
            kagune_type_bit=KaguneType.UKAKU.value["bit"],
            kagune_strength_ukaku=1,
        )

        (reply,) = await send("растить кагуне", uid=UID)

        assert matches_phrase(reply, "errors.not_enough_money")
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.kagune_strength_ukaku == 1

    async def test_multiple_types_shows_choice_keyboard(self, feed, session_factory):
        await seed(session_factory, UID, "Вася", balance=100000)
        await seed_ghoul(
            session_factory,
            UID,
            kagune_type_bit=KaguneType.UKAKU.value["bit"]
            | KaguneType.KOUKAKU.value["bit"],
            kagune_strength_ukaku=1,
            kagune_strength_koukaku=1,
        )

        telegram = await feed(message_update("растить кагуне", uid=UID))

        (body,) = telegram.bodies("sendMessage")
        assert matches_phrase(body["text"], "kagune.upgrade.choice.message")
        choice = Dialogs.kagune.upgrade.choice
        ukaku = only_text(choice.button(kagune="Укаку", price=150))
        koukaku = only_text(choice.button(kagune="Коукаку", price=150))
        assert button_data(body, ukaku) == f"kagune_upgrade:{UID}:ukaku"
        assert button_data(body, koukaku) == f"kagune_upgrade:{UID}:koukaku"


class TestKaguneChoice:
    async def _seed_two_types(self, session_factory) -> None:
        await seed(session_factory, UID, "Вася", balance=100000)
        await seed_ghoul(
            session_factory,
            UID,
            kagune_type_bit=KaguneType.UKAKU.value["bit"]
            | KaguneType.KOUKAKU.value["bit"],
            kagune_strength_ukaku=1,
            kagune_strength_koukaku=1,
        )

    async def test_correct_invoker_upgrades_and_deletes_keyboard_message(
        self, feed, telegram, session_factory, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        await self._seed_two_types(session_factory)
        await seed_cooldown_type(session_factory, "KAGUNE_UPGRADE", duration=600)

        telegram = await feed(callback_update(f"kagune_upgrade:{UID}:ukaku", uid=UID))

        assert telegram.methods_called("deleteMessage") == 1
        (body,) = telegram.bodies("sendMessage")
        assert matches_phrase(body["text"], "kagune.upgrade.done")

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.kagune_strength_ukaku == 2

    async def test_wrong_invoker_press_only_stops_the_spinner(
        self, feed, telegram, session_factory
    ):
        await self._seed_two_types(session_factory)
        # GhoulMiddleware не бывает bypass для callback — чужой должен быть реальным
        # гулем, иначе его блокирует "Ты не гуль", а не тишина pressed_by
        await seed(session_factory, UID + 1, "Чужой")
        await seed_ghoul(session_factory, UID + 1)

        telegram = await feed(
            callback_update(f"kagune_upgrade:{UID}:ukaku", uid=UID + 1)
        )

        # pressed_by("invoker_id") не пропускает чужое нажатие ни в один хендлер — диспетчер
        # только останавливает «часики» пустым ответом, без алерта и правок
        assert telegram.calls == [("answerCallbackQuery", {"callback_query_id": "cq1"})]

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.kagune_strength_ukaku == 1

    async def test_cooldown_between_keyboard_and_press_gives_alert(
        self, feed, telegram, session_factory
    ):
        await self._seed_two_types(session_factory)
        await seed_active_cooldown(session_factory, UID, "KAGUNE_UPGRADE")

        telegram = await feed(callback_update(f"kagune_upgrade:{UID}:ukaku", uid=UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert matches_phrase(answer["text"], "kagune.upgrade.cooldown")
        assert answer["show_alert"] is True
        assert telegram.methods_called("deleteMessage") == 0


class TestSnap:
    @pytest.mark.parametrize("text", ["щелк", "щёлк", "Щелк", "ЩЁЛК"])
    async def test_accepts_without_gif_when_folder_is_empty(
        self, send, session_factory, monkeypatch, tmp_path, text
    ):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=0)
        await seed_cooldown_type(session_factory, "SNAP", duration=1800)

        (reply,) = await send(text, uid=UID)

        assert matches_phrase(reply, "snap.done")
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.snap_count == 1
        user = await get_user(session_factory, UID)
        assert user is not None and user.balance > 0

    async def test_sends_gif_when_one_exists(
        self, feed, telegram, session_factory, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        folder = tmp_path / "animation" / "snap_finger"
        folder.mkdir(parents=True)
        (folder / "snap.mp4").write_bytes(b"gif-bytes")
        telegram.results["sendAnimation"] = {
            "message_id": 1,
            "date": 5,
            "chat": {"id": UID, "type": "private"},
            "animation": {
                "file_id": "NEW_ID",
                "file_unique_id": "u",
                "width": 1,
                "height": 1,
                "duration": 1,
            },
        }
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=0)
        await seed_cooldown_type(session_factory, "SNAP", duration=1800)

        await feed(message_update("щелк", uid=UID))

        (body,) = telegram.bodies("sendAnimation")
        assert body["animation"] == "<file:snap.mp4>"
        # файл уходит multipart'ом: не-строковые поля приезжают JSON-строкой
        assert json.loads(body["reply_parameters"])["message_id"] == 1

    async def test_cooldown_reply(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=0)
        await seed_active_cooldown(session_factory, UID, "SNAP")

        (reply,) = await send("щелк", uid=UID)

        assert matches_phrase(reply, "snap.cooldown")
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.snap_count == 0


def base_power(ghoul: Ghoul) -> int:
    kagune = (
        (ghoul.kagune_strength_ukaku or 0)
        + (ghoul.kagune_strength_koukaku or 0)
        + (ghoul.kagune_strength_rinkaku or 0)
        + (ghoul.kagune_strength_bikaku or 0)
    )
    stats = ghoul.strength + ghoul.dexterity + ghoul.speed + ghoul.max_health + ghoul.regeneration
    return stats + kagune


class TestTopPower:
    async def test_base_power_order_with_danger_rank(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed(session_factory, UID + 1, "Петя")
        await seed_ghoul(session_factory, UID)
        await seed_ghoul(session_factory, UID + 1, strength=1000, hunger=0)
        petya = await get_ghoul(session_factory, UID + 1)
        assert petya is not None

        (reply,) = await send("топ бм", uid=UID)

        assert reply.startswith(only_text(Dialogs.tops.power_title(count=20)))
        # сила 1000 плюс стартовые статы — мощь 1000–1499, ранг C; голод на место не влияет
        value = only_text(Dialogs.tops.power_value(power=base_power(petya), rank="C"))
        first = only_text(Dialogs.tops.row(place=1, name="Петя", value=value))
        assert first in reply.splitlines()
        assert reply.index("Петя") < reply.index("Вася")


class TestTopSnap:
    # "нету топа" (пустой топ) недостижима и у прода, и в порту: GhoulMiddleware
    # не пускает в хендлер никого, кроме живого гуля — значит хотя бы сам
    # отправитель в топе всегда есть.

    async def test_default_count_and_ordering(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed(session_factory, UID + 1, "Петя")
        await seed_ghoul(session_factory, UID, snap_count=5)
        await seed_ghoul(session_factory, UID + 1, snap_count=10)

        (reply,) = await send("топ щелк", uid=UID)

        assert reply.startswith(only_text(Dialogs.tops.snap_title(count=20)))
        assert reply.index("Петя") < reply.index("Вася")  # больше щелчков — выше

    async def test_explicit_count(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=1)

        (reply,) = await send("топ щелк 3", uid=UID)

        assert reply.startswith(only_text(Dialogs.tops.snap_title(count=3)))

    async def test_non_digit_count(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        (reply,) = await send("топ щелк абв", uid=UID)

        assert matches_phrase(reply, "tops.not_a_number")

    async def test_count_out_of_range(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        (reply,) = await send("топ щелк 51", uid=UID)

        assert matches_phrase(reply, "tops.out_of_range")

    @pytest.mark.parametrize(
        ("text", "reply"),
        [
            # как у прода (isdigit): отрицательное — "не цифра", а 0 — вне диапазона
            ("топ щелк -5", "tops.not_a_number"),
            ("топ щелк 0", "tops.out_of_range"),
            ("Топ Щелк 2 лишнее", None),  # регистр и хвост после числа не мешают
        ],
    )
    async def test_count_edge_cases(self, send, session_factory, text, reply):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        (answer,) = await send(text, uid=UID)

        if reply is None:
            assert answer.startswith(only_text(Dialogs.tops.snap_title(count=2)))
        else:
            assert matches_phrase(answer, reply)

    async def test_longer_word_is_not_a_command(self, send, session_factory):
        # исправленный прод-баг: "топ щелкает" ловилось по началу текста и падало
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        assert await send("топ щелкает", uid=UID) == []


class TestTopKagune:
    async def test_count_errors_like_top_snap(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        (not_a_number,) = await send("топ кагуне абв", uid=UID)
        assert matches_phrase(not_a_number, "tops.not_a_number")
        (out_of_range,) = await send("топ кагуне 99", uid=UID)
        assert matches_phrase(out_of_range, "tops.out_of_range")

    async def test_sum_view_with_keyboard(self, feed, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(
            session_factory,
            UID,
            kagune_type_bit=KaguneType.UKAKU.value["bit"],
            kagune_strength_ukaku=7,
        )

        telegram = await feed(message_update("топ кагуне", uid=UID))

        (body,) = telegram.bodies("sendMessage")
        assert body["text"].startswith(only_text(Dialogs.tops.kagune.sum_title(count=20)))
        assert only_text(Dialogs.tops.row(place=1, name="Вася", value=7)) in body["text"]
        for label in ("Укаку", "Коукаку", "Ринкаку", "Бикаку"):
            assert button_data(body, label) is not None

    async def test_switching_view_via_callback(self, feed, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(
            session_factory,
            UID,
            kagune_type_bit=KaguneType.UKAKU.value["bit"],
            kagune_strength_ukaku=7,
        )

        telegram = await feed(message_update("топ кагуне", uid=UID))
        (body,) = telegram.bodies("sendMessage")
        data = button_data(body, "Укаку")

        telegram = await feed(callback_update(data, uid=UID))

        (edited,) = telegram.bodies("editMessageText")
        title = Dialogs.tops.kagune.type_title(count=20, kagune="Укаку")
        assert edited["text"].startswith(only_text(title))
        assert only_text(Dialogs.tops.row(place=1, name="Вася", value=7)) in edited["text"]
        back = f"⬅️ {only_text(Dialogs.tops.kagune.sum_button())}"
        assert button_data(edited, back) is not None

    async def test_malformed_callback_data(self, feed, telegram, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        result = await feed(
            callback_update("topkagune:not_a_number:sum:ukaku", uid=UID)
        )

        (answer,) = result.bodies("answerCallbackQuery")
        assert answer["text"] == only_text(Dialogs.tops.kagune.bad_button())
        assert result.methods_called("editMessageText") == 0

    async def test_inaccessible_message(self, feed, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)
        update = callback_update("topkagune:20:sum:ukaku", uid=UID)
        # сообщение старше 48 часов: Telegram отдаёт InaccessibleMessage (date=0)
        update["callback_query"]["message"] = {
            "message_id": 44,
            "date": 0,
            "chat": {"id": UID, "type": "private", "first_name": "Вася"},
        }

        result = await feed(update)

        (answer,) = result.bodies("answerCallbackQuery")
        assert answer["text"] == only_text(Dialogs.errors.cannot_process())


def group_callback_update(data: str, uid: int, chat: int = -100500) -> dict:
    """Нажатие кнопки под сообщением в группе (callback_update — всегда личка)."""
    update = callback_update(data, uid=uid)
    update["callback_query"]["message"]["chat"] = chat_dict(chat)
    return update


class TestUpgradeStat:
    @staticmethod
    def row(current: int, x5: object, x10: object) -> str:
        stat = STAT_LABELS["strength"]
        return only_text(Dialogs.stats.shop.row(stat=stat, current=current, x5=x5, x10=x10))

    async def test_group_is_refused(self, send, telegram, session_factory):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        assert await send("качаться", uid=UID, chat=-100500) == [
            only_text(Dialogs.stats.private_only())
        ]

    async def test_shop_text_and_buttons(self, feed, session_factory):
        await seed(session_factory, UID, "Вася", balance=12345)
        await seed_ghoul(session_factory, UID, strength=1, level=1)

        telegram = await feed(message_update("Качаться", uid=UID))

        (body,) = telegram.bodies("sendMessage")
        assert matches_phrase(body["text"], "stats.shop.message")
        assert format_amount(12345) in body["text"]
        price5 = STAT_UPGRADE_CONFIG.price(1, 5, "strength")
        price10 = STAT_UPGRADE_CONFIG.price(1, 10, "strength")
        row = self.row(current=1, x5=price5, x10=price10)
        assert row in body["text"].split("\n")
        price1 = STAT_UPGRADE_CONFIG.price(1, 1, "strength")
        assert button_data(body, f"💪 +1 ({price1})") == "stat_buy:strength:1"
        assert button_data(body, f"💪 +10 ({price10})") == "stat_buy:strength:10"

    async def test_capped_stat_shows_nop_buttons(self, feed, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, strength=98, level=1)  # потолок 100

        telegram = await feed(message_update("качаться", uid=UID))

        (body,) = telegram.bodies("sendMessage")
        price2 = STAT_UPGRADE_CONFIG.price(98, 2, "strength")
        # у прода в тексте и на кнопках — цена того, что реально влезет до потолка
        assert self.row(current=98, x5=price2, x10=price2) in body["text"].split("\n")
        assert button_data(body, f"💪 +5 ({price2})") == "stat_buy:strength:5"

        await seed_ghoul(session_factory, UID, strength=100)
        telegram = await feed(message_update("качаться", uid=UID))
        (body,) = telegram.bodies("sendMessage")
        assert self.row(current=100, x5="—", x10="—") in body["text"].split("\n")
        assert button_data(body, "💪 +1 (—)") == "stat_nop"

    async def test_buy_edits_shop_and_answers(self, feed, session_factory):
        await seed(session_factory, UID, "Вася", balance=100000)
        await seed_ghoul(session_factory, UID, strength=1, level=1)
        price = STAT_UPGRADE_CONFIG.price(1, 5, "strength")

        telegram = await feed(callback_update("stat_buy:strength:5", uid=UID))

        (edited,) = telegram.bodies("editMessageText")
        assert matches_phrase(edited["text"], "stats.shop.message")
        assert format_amount(100000 - price) in edited["text"]
        row = self.row(
            current=6,
            x5=STAT_UPGRADE_CONFIG.price(6, 5, "strength"),
            x10=STAT_UPGRADE_CONFIG.price(6, 10, "strength"),
        )
        assert row in edited["text"].split("\n")
        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == only_text(
            Dialogs.stats.bought(stat=STAT_LABELS["strength"], count=5, price=price)
        )

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.strength == 6
        assert await balance_of(session_factory, UID) == 100000 - price

    async def test_buy_max_health_heals_by_the_same_amount(self, feed, session_factory):
        await seed(session_factory, UID, "Вася", balance=100000)
        await seed_ghoul(session_factory, UID, max_health=5, health=3, level=1)

        await feed(callback_update("stat_buy:max_health:1", uid=UID))

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None
        assert (ghoul.max_health, ghoul.health) == (6, 4)

    async def test_buy_over_cap_buys_only_the_rest(self, feed, session_factory):
        await seed(session_factory, UID, "Вася", balance=100000)
        await seed_ghoul(session_factory, UID, strength=98, level=1)
        price = STAT_UPGRADE_CONFIG.price(98, 2, "strength")

        telegram = await feed(callback_update("stat_buy:strength:10", uid=UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == only_text(
            Dialogs.stats.bought(stat=STAT_LABELS["strength"], count=2, price=price)
        )

    async def test_not_enough_money(self, feed, session_factory):
        await seed(session_factory, UID, "Вася", balance=0)
        await seed_ghoul(session_factory, UID, strength=1, level=1)

        telegram = await feed(callback_update("stat_buy:strength:1", uid=UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert matches_phrase(answer["text"], "stats.no_money")
        assert telegram.methods_called("editMessageText") == 0
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.strength == 1

    async def test_buy_at_cap(self, feed, session_factory):
        await seed(session_factory, UID, "Вася", balance=100000)
        await seed_ghoul(session_factory, UID, strength=100, level=1)

        telegram = await feed(callback_update("stat_buy:strength:1", uid=UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == only_text(Dialogs.stats.limit())
        assert await balance_of(session_factory, UID) == 100000

    async def test_nop_button(self, feed, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        telegram = await feed(callback_update("stat_nop", uid=UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == only_text(Dialogs.stats.limit())

    @pytest.mark.parametrize("data", ["stat_nop", "stat_buy:strength:1"])
    async def test_press_in_group_is_refused(self, feed, session_factory, data):
        await seed(session_factory, UID, "Вася", balance=100000)
        await seed_ghoul(session_factory, UID, strength=1, level=1)

        telegram = await feed(group_callback_update(data, uid=UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == only_text(Dialogs.stats.private_only_action())
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.strength == 1


class TestRegenStatus:
    async def test_full_health(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, health=5, max_health=5)

        (reply,) = await send("Реген", uid=UID)

        assert matches_phrase(reply, "status.regen") and "5/5" in reply
        assert reply.endswith(only_text(Dialogs.status.healthy()))

    async def test_time_until_full_health(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(
            session_factory,
            UID,
            health=1,
            max_health=500,
            regeneration=3,
            hunger=100,
            kagune_type_bit=KaguneType.UKAKU.value["bit"],
        )

        (reply,) = await send("реген", uid=UID)

        per_hour = health_regen_per_hour(3, 100, KaguneType.UKAKU.value["bit"], False)
        hours = hours_until_full_health(1, 500, per_hour)
        assert hours is not None
        until = Dialogs.status.until_healthy(duration=format_duration(int(hours * 3600)))
        assert reply == only_text(
            Dialogs.status.regen(
                health=1,
                max_health=500,
                hp_per_hour=round(per_hour, 2),
                time_left=only_text(until),
            )
        )

    async def test_zero_regeneration_never_heals(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, health=1, max_health=500, regeneration=0)

        (reply,) = await send("реген", uid=UID)

        assert reply.endswith(only_text(Dialogs.status.no_regen()))


class TestHungerStatus:
    async def test_status_with_effective_stats(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(
            session_factory,
            UID,
            hunger=80,
            strength=10,
            kagune_type_bit=KaguneType.UKAKU.value["bit"],
            kagune_strength_ukaku=4,
        )

        (reply,) = await send("Голод", uid=UID)

        tier = get_hunger_tier(80)
        assert matches_phrase(reply, "status.hunger")
        assert tier.name in reply
        assert str(tier.falling_multiplier) in reply and str(tier.rising_multiplier) in reply

    async def test_starved(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, hunger=0)

        (reply,) = await send("голод", uid=UID)

        assert only_text(Dialogs.status.starved()) in reply


class FakeQuiz:
    """Вместо QuizService: внешний API в тестах недоступен."""

    def __init__(self, options: list[str], answer: str) -> None:
        self.question = Question(
            id=17, question="Кто?", answer_options=options, answer_group="g"
        )
        self.answer = Answer(
            id=17, question="Кто?", answer=answer, answer_group="g"
        )
        self.whois = WhoisQuestion(
            id=21,
            prompt_media=Media(url="https://x/pic.jpg", kind="image"),
            answer_options=options,
        )
        self.whois_answer = WhoisAnswer(id=21, answer=answer)
        self.true_false = TrueFalseQuestion(id=33, statement="Канеки — гуль")
        self.truth = TrueFalseAnswer(id=33, correct=True)
        self.whois_enabled = True

    async def get_random_quiz(self) -> Question:
        return self.question

    async def get_answer_by_id(self, question_id: int) -> Answer:
        assert question_id == self.question.id
        return self.answer

    async def get_random_whois(self) -> WhoisQuestion:
        if not self.whois_enabled:
            raise QuizModeDisabled()
        return self.whois

    async def get_whois_answer(self, question_id: int) -> WhoisAnswer:
        assert question_id == self.whois.id
        return self.whois_answer

    async def get_random_true_false(self) -> TrueFalseQuestion:
        return self.true_false

    async def get_true_false_answer(self, question_id: int) -> TrueFalseAnswer:
        assert question_id == self.true_false.id
        return self.truth


PHOTO = "https://x/pic.jpg"
SEND = "sendRichMessage"


def incoming_block(block: dict) -> dict:
    """Блок rich-сообщения, как его присылает Telegram: медиа — с file_id вместо ссылки."""
    if block["type"] == "photo":
        photo = {"file_id": block["photo"]["media"], "file_unique_id": "u", "width": 1, "height": 1}
        return {"type": "photo", "photo": [photo]}
    if block["type"] == "video":
        video = {
            "file_id": block["video"]["media"],
            "file_unique_id": "u",
            "width": 1,
            "height": 1,
            "duration": 1,
        }
        return {"type": "video", "video": video}
    return block


def keyboard_callback(body: dict, label: str, uid: int) -> dict:
    """Нажатие кнопки label под сообщением body, с содержимым и клавиатурой этого сообщения."""
    update = callback_update(button_data(body, label), uid=uid)
    message = update["callback_query"]["message"]
    message["reply_markup"] = body["reply_markup"]
    del message["text"]
    blocks = [incoming_block(block) for block in body["rich_message"]["blocks"]]
    message["rich_message"] = {"blocks": blocks}
    return update


def lines(body: dict) -> list[str]:
    return rich_texts(body["rich_message"])


def block_types(body: dict) -> list[str]:
    return [block["type"] for block in body["rich_message"]["blocks"]]


def normalized(text: str) -> str:
    return "\n".join(line for line in text.split("\n") if line)


def result_variants(answer: str, choice: str, status) -> set[str]:
    variants = phrase_texts(Dialogs.quiz.result(answer=answer, choice=choice, status=status))
    return {normalized(text) for text in variants}


def result_text(body: dict, question_lines: int = 1) -> str:
    return "\n".join(lines(body)[question_lines:])


async def streak_rows(session_factory) -> list[QuizStreak]:
    async with session_factory() as session:
        return list((await session.scalars(select(QuizStreak))).all())


async def expire_streaks(session_factory) -> None:
    async with session_factory() as session:
        await session.execute(
            update(QuizStreak).values(expires_at=func.now() - timedelta(seconds=1))
        )
        await session.commit()


class TestQuiz:
    OPTIONS = ["Канеки", "Тоука", "Хинами", "Ута"]
    AGAIN = only_text(Dialogs.quiz.play_again())

    @pytest.fixture
    def quiz(self, dispatcher, monkeypatch) -> FakeQuiz:
        fake = FakeQuiz(self.OPTIONS, answer="Канеки")
        monkeypatch.setattr(dispatcher, "quiz_service", fake)
        monkeypatch.setattr(QUIZ_CONFIG, "whois_chance", 0.0)
        monkeypatch.setattr(QUIZ_CONFIG, "true_false_chance", 0.0)
        return fake

    @pytest.fixture
    def whois_only(self, quiz, monkeypatch) -> FakeQuiz:
        monkeypatch.setattr(QUIZ_CONFIG, "whois_chance", 1.0)
        return quiz

    @pytest.fixture
    def true_false_only(self, quiz, monkeypatch) -> FakeQuiz:
        monkeypatch.setattr(QUIZ_CONFIG, "true_false_chance", 1.0)
        return quiz

    async def _ask(self, feed, session_factory, uid: int = UID) -> dict:
        await seed(session_factory, uid, "Вася")
        await seed_ghoul(session_factory, uid)
        telegram = await feed(message_update("/quiz", uid=uid))
        (body,) = telegram.bodies(SEND)
        return body

    async def _answer(self, feed, body: dict, label: str) -> dict:
        telegram = await feed(keyboard_callback(body, label, UID))
        (edited,) = telegram.bodies("editMessageText")
        return edited

    async def _next(self, feed, result: dict) -> dict:
        telegram = await feed(keyboard_callback(result, self.AGAIN, UID))
        (question,) = telegram.bodies(SEND)
        return question

    async def test_question_is_a_rich_message_with_four_options(
        self, feed, session_factory, quiz
    ):
        body = await self._ask(feed, session_factory)

        assert lines(body) == ["Кто?"]
        assert body["reply_parameters"]["message_id"] == 1
        rows = body["reply_markup"]["inline_keyboard"]
        assert [len(row) for row in rows] == [2, 2]
        labels = [b["text"] for row in rows for b in row]
        assert sorted(labels) == sorted(self.OPTIONS)
        assert button_data(body, labels[3]) == f"quiz_answer:17:3:0:0:{UID}"

    async def test_correct_answer_pays_and_offers_restart(
        self, feed, session_factory, quiz
    ):
        body = await self._ask(feed, session_factory)

        telegram = await feed(keyboard_callback(body, "Канеки", UID))

        (edited,) = telegram.bodies("editMessageText")
        award = await balance_of(session_factory, UID)
        assert award > 0
        assert lines(edited)[0] == "Кто?"
        status = Dialogs.quiz.correct(award=award, streak=1, multiplier="1", minutes=5)
        assert result_text(edited) in result_variants("Канеки", "Канеки", status)
        assert button_data(edited, self.AGAIN) == f"quiz_restart:{UID}"
        # как у прода: часики на кнопке не закрываются
        assert telegram.methods_called("answerCallbackQuery") == 0

    async def test_wrong_answer(self, feed, session_factory, quiz):
        body = await self._ask(feed, session_factory)

        edited = await self._answer(feed, body, "Тоука")

        assert result_text(edited) in result_variants("Канеки", "Тоука", Dialogs.quiz.wrong())
        assert await balance_of(session_factory, UID) == 0

    async def test_second_answer_is_not_active(self, feed, session_factory, quiz):
        body = await self._ask(feed, session_factory)
        await feed(keyboard_callback(body, "Тоука", UID))

        telegram = await feed(keyboard_callback(body, "Канеки", UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == only_text(Dialogs.quiz.not_active())
        assert await balance_of(session_factory, UID) == 0

    async def test_someone_elses_quiz_is_not_theirs(self, feed, session_factory, quiz):
        body = await self._ask(feed, session_factory)
        await seed(session_factory, UID + 1, "Петя")
        await seed_ghoul(session_factory, UID + 1)

        telegram = await feed(keyboard_callback(body, "Канеки", UID + 1))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == only_text(Dialogs.quiz.not_yours())
        assert await balance_of(session_factory, UID + 1) == 0

    async def test_someone_elses_restart_keeps_the_streak(self, feed, session_factory, quiz):
        body = await self._ask(feed, session_factory)
        result = await self._answer(feed, body, "Канеки")
        await seed(session_factory, UID + 1, "Петя")
        await seed_ghoul(session_factory, UID + 1)

        telegram = await feed(keyboard_callback(result, self.AGAIN, UID + 1))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == only_text(Dialogs.quiz.not_yours())
        assert telegram.methods_called(SEND) == 0
        assert [row.streak for row in await streak_rows(session_factory)] == [1]

    @pytest.mark.parametrize("trigger", ["квиз", "Викторина", "/quiz"])
    async def test_triggers(self, feed, session_factory, quiz, trigger):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        telegram = await feed(message_update(trigger, uid=UID))

        (body,) = telegram.bodies(SEND)
        assert lines(body) == ["Кто?"]

    async def test_play_again_sends_a_new_question_and_closes_the_old_one(
        self, feed, session_factory, quiz
    ):
        body = await self._ask(feed, session_factory)
        result = await self._answer(feed, body, "Тоука")

        telegram = await feed(keyboard_callback(result, self.AGAIN, UID))

        (question,) = telegram.bodies(SEND)
        assert lines(question) == ["Кто?"]
        assert "reply_parameters" not in question
        assert telegram.methods_called("editMessageReplyMarkup") == 1
        result = await self._answer(feed, question, "Канеки")
        assert lines(result)[0] == "Кто?"
        assert await balance_of(session_factory, UID) > 0

    async def test_streak_raises_the_award(self, feed, session_factory, quiz):
        body = await self._ask(feed, session_factory)
        result = await self._answer(feed, body, "Канеки")
        first = await balance_of(session_factory, UID)

        question = await self._next(feed, result)
        assert button_data(question, "Канеки").endswith(f":1:0:{UID}")
        await self._answer(feed, question, "Канеки")

        second = await balance_of(session_factory, UID) - first
        assert 5000 * 1.25 <= second <= 10000 * 1.25

    async def test_wrong_answer_breaks_the_streak(self, feed, session_factory, quiz):
        body = await self._ask(feed, session_factory)
        result = await self._answer(feed, body, "Канеки")
        question = await self._next(feed, result)

        edited = await self._answer(feed, question, "Тоука")

        status = Dialogs.quiz.wrong_streak(streak=1)
        assert result_text(edited) in result_variants("Канеки", "Тоука", status)
        assert await streak_rows(session_factory) == []

    async def test_streak_burns_if_continued_late(self, feed, session_factory, quiz):
        body = await self._ask(feed, session_factory)
        result = await self._answer(feed, body, "Канеки")
        await expire_streaks(session_factory)

        question = await self._next(feed, result)

        assert lines(question) == ["Кто?", only_text(Dialogs.quiz.streak_expired(streak=1))]
        assert button_data(question, "Канеки").endswith(f":0:0:{UID}")

    async def test_ticker_breaks_the_streak_by_itself(
        self, feed, session_factory, quiz, dispatcher, telegram
    ):
        body = await self._ask(feed, session_factory)
        result = await self._answer(feed, body, "Канеки")
        telegram.calls.clear()
        await dispatcher.run_task(QuizStreakExpiry)
        assert telegram.calls == []
        await expire_streaks(session_factory)

        await dispatcher.run_task(QuizStreakExpiry)

        (edited,) = telegram.bodies("editMessageText")
        broken = only_text(Dialogs.quiz.streak_broken(streak=1))
        assert lines(edited) == [*lines(result), broken]
        assert "reply_markup" not in edited
        assert await streak_rows(session_factory) == []

    async def test_whois_is_a_heading_with_a_photo(self, feed, session_factory, whois_only):
        body = await self._ask(feed, session_factory)

        assert block_types(body) == ["heading", "photo"]
        assert lines(body) == [only_text(Dialogs.quiz.whois_title())]
        assert body["rich_message"]["blocks"][1]["photo"]["media"] == PHOTO
        assert button_data(body, "Канеки").endswith(f":0:1:{UID}")

    async def test_whois_video_is_a_video_block(self, feed, session_factory, whois_only):
        whois_only.whois.prompt_media = Media(url="https://x/clip.mp4", kind="video")

        body = await self._ask(feed, session_factory)

        assert block_types(body) == ["heading", "video"]

    async def test_whois_result_keeps_the_photo(self, feed, session_factory, whois_only):
        body = await self._ask(feed, session_factory)

        edited = await self._answer(feed, body, "Канеки")

        award = await balance_of(session_factory, UID)
        assert award > 0
        assert block_types(edited)[:2] == ["heading", "photo"]
        assert edited["rich_message"]["blocks"][1]["photo"]["media"] == PHOTO
        status = Dialogs.quiz.correct(award=award, streak=1, multiplier="1", minutes=5)
        assert result_text(edited) in result_variants("Канеки", "Канеки", status)

    async def test_next_question_after_a_photo_is_a_new_message(
        self, feed, session_factory, whois_only, monkeypatch
    ):
        body = await self._ask(feed, session_factory)
        result = await self._answer(feed, body, "Канеки")
        monkeypatch.setattr(QUIZ_CONFIG, "whois_chance", 0.0)

        question = await self._next(feed, result)

        assert block_types(question) == ["paragraph"]
        assert button_data(question, "Канеки").endswith(f":1:0:{UID}")

    async def test_answer_illustration_is_shown_in_the_result(
        self, feed, session_factory, quiz
    ):
        quiz.answer.answer_media = Media(url="https://x/kaneki.jpg", kind="image")
        body = await self._ask(feed, session_factory)

        edited = await self._answer(feed, body, "Канеки")

        assert block_types(edited)[-1] == "photo"
        assert edited["rich_message"]["blocks"][-1]["photo"]["media"] == "https://x/kaneki.jpg"

    async def test_result_without_illustration_when_telegram_cannot_fetch_it(
        self, feed, session_factory, quiz, telegram
    ):
        quiz.answer.answer_media = Media(url="https://x/kaneki.jpg", kind="image")
        body = await self._ask(feed, session_factory)
        telegram.fail_next(
            "editMessageText",
            "rich_message",
            lambda rich: "https://x/kaneki.jpg" in json.dumps(rich),
            description="Bad Request: failed to get HTTP URL content",
        )

        await feed(keyboard_callback(body, "Канеки", UID))

        failed, edited = telegram.bodies("editMessageText")
        assert "photo" in block_types(failed)
        assert "photo" not in block_types(edited)
        assert lines(edited)[0] == "Кто?"

    async def test_ticker_rewrites_the_rich_result(
        self, feed, session_factory, whois_only, dispatcher, telegram
    ):
        body = await self._ask(feed, session_factory)
        result = await self._answer(feed, body, "Канеки")
        await expire_streaks(session_factory)
        telegram.calls.clear()

        await dispatcher.run_task(QuizStreakExpiry)

        (edited,) = telegram.bodies("editMessageText")
        broken = only_text(Dialogs.quiz.streak_broken(streak=1))
        assert lines(edited) == [*lines(result), broken]
        assert block_types(edited)[:2] == ["heading", "photo"]

    async def test_disabled_mode_falls_back_to_a_text_question(
        self, feed, session_factory, whois_only
    ):
        whois_only.whois_enabled = False

        body = await self._ask(feed, session_factory)

        assert lines(body) == ["Кто?"]

    async def test_media_telegram_cannot_fetch_falls_back_to_a_text_question(
        self, feed, session_factory, whois_only, telegram
    ):
        telegram.fail_next(
            SEND,
            "rich_message",
            lambda rich: PHOTO in json.dumps(rich),
            description="Bad Request: failed to get HTTP URL content",
        )

        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        await feed(message_update("/quiz", uid=UID))

        failed, body = telegram.bodies(SEND)
        assert "photo" in block_types(failed)
        assert lines(body) == ["Кто?"]
        assert block_types(body) == ["paragraph"]

    async def test_true_false_has_two_buttons(self, feed, session_factory, true_false_only):
        body = await self._ask(feed, session_factory)

        assert block_types(body) == ["heading", "paragraph"]
        assert lines(body) == [only_text(Dialogs.quiz.true_false_title()), "Канеки — гуль"]
        labels = [b["text"] for row in body["reply_markup"]["inline_keyboard"] for b in row]
        assert labels == [
            only_text(Dialogs.quiz.true_button()),
            only_text(Dialogs.quiz.false_button()),
        ]
        assert button_data(body, labels[1]) == f"quiz_answer:33:1:0:2:{UID}"

    async def test_true_false_with_a_picture(self, feed, session_factory, true_false_only):
        true_false_only.true_false.prompt_media = Media(url=PHOTO, kind="image")

        body = await self._ask(feed, session_factory)

        assert block_types(body) == ["heading", "paragraph", "photo"]

    async def test_true_false_pays_part_of_the_award(
        self, feed, session_factory, true_false_only
    ):
        body = await self._ask(feed, session_factory)

        edited = await self._answer(feed, body, only_text(Dialogs.quiz.true_button()))

        award = await balance_of(session_factory, UID)
        share = QUIZ_CONFIG.true_false_share
        assert 5000 * share <= award <= 10000 * share
        assert lines(edited)[:2] == [
            only_text(Dialogs.quiz.true_false_title()),
            "Канеки — гуль",
        ]

    async def test_true_false_wrong(self, feed, session_factory, true_false_only):
        body = await self._ask(feed, session_factory)

        edited = await self._answer(feed, body, only_text(Dialogs.quiz.false_button()))

        assert await balance_of(session_factory, UID) == 0
        true_label = only_text(Dialogs.quiz.true_button())
        false_label = only_text(Dialogs.quiz.false_button())
        assert result_text(edited, 2) in result_variants(
            true_label, false_label, Dialogs.quiz.wrong()
        )

    async def test_long_option_fits_the_button(
        self, feed, session_factory, dispatcher, monkeypatch
    ):
        # у прода текст варианта едет в callback_data и такой вопрос не отправить
        long = "Кен Канеки после встречи с Ризе Камиширо"
        fake = FakeQuiz([long, "а_б", "в", "г"], answer=long)
        monkeypatch.setattr(dispatcher, "quiz_service", fake)
        monkeypatch.setattr(QUIZ_CONFIG, "whois_chance", 0.0)
        monkeypatch.setattr(QUIZ_CONFIG, "true_false_chance", 0.0)
        body = await self._ask(feed, session_factory)

        edited = await self._answer(feed, body, long)

        award = await balance_of(session_factory, UID)
        status = Dialogs.quiz.correct(award=award, streak=1, multiplier="1", minutes=5)
        assert result_text(edited) in result_variants(long, long, status)


class TestCombatPower:
    async def _seed(self, session_factory) -> Ghoul:
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(
            session_factory,
            UID,
            strength=10,
            max_health=50,
            health=20,
            hunger=100,
            kagune_type_bit=KaguneType.UKAKU.value["bit"],
            kagune_strength_ukaku=4,
        )
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None
        return ghoul

    async def test_rich_tables(self, feed, session_factory):
        await self._seed(session_factory)

        telegram = await feed(message_update("Боевая мощь", uid=UID))

        (rich,) = telegram.bodies("sendRichMessage")
        blocks = rich["rich_message"]["blocks"]
        # у БД-пользователя без фамилии full_name с пробелом на конце, как у прода
        assert matches_phrase(blocks[0]["text"], "combat_power.rich.title")
        assert blocks[0]["text"].endswith("Вася ")
        vacuum = [[c["text"] for c in row] for row in blocks[1]["cells"]]
        assert vacuum[1] == ["Сила", "10"]
        assert vacuum[4] == ["Здоровье", "50"]  # паспортный max_health
        assert vacuum[6] == ["Кагуне", "4"]
        combat = [[c["text"] for c in row] for row in blocks[4]["cells"]]
        assert combat[0] == ["Стат", "Значение", "Влияние голода", "Влияние кагуне"]
        assert combat[4][:2] == ["Здоровье", "20"]  # текущее health
        assert telegram.sent == []

    async def test_plain_text_when_rich_fails(self, feed, telegram, session_factory):
        await self._seed(session_factory)
        telegram.errors["sendRichMessage"] = (400, "Bad Request: rich not supported")

        (reply,) = (await feed(message_update("боевая мощь", uid=UID))).sent

        assert matches_phrase(reply, "combat_power.full")

    async def test_short_alias(self, send, session_factory):
        ghoul = await self._seed(session_factory)
        power = sum(
            (ghoul.strength, ghoul.dexterity, ghoul.speed, ghoul.max_health)
        ) + (ghoul.regeneration + 4)  # + сила кагуне

        (reply,) = await send("БМ", uid=UID)

        assert matches_phrase(reply, "combat_power.short") and str(power) in reply
