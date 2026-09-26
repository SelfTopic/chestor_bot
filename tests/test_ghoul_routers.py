"""routers/ghoul_routers: GhoulMiddleware гейтит весь роутер (без гуля — молчание с
подсказкой, кроме "растить кагуне"; мёртвому гулю тоже отказ). coffee.py: использует
оба новых ctx-хелпера (reply_gif через media_paths.random_media; кулдаун — не через
ctx.cooldown_remaining, а CoffeeService.execute_cooldown, который сам решает COFFEE
это или COFFEE_DAY, см. coffee.py). upgrade_kagune/: единственная команда, доступная
и без гуля (регистрация), и мёртвому гулю (возрождение) — bypass в GhoulMiddleware;
типизированный KaguneUpgradePress вместо ручного parse_kagune_callback_payload."""

import json

import pytest
from ghoul_quiz import Answer, Question

from src.bot.config import game_config
from src.bot.game_configs import STAT_UPGRADE_CONFIG
from src.bot.repositories import GhoulRepository, UserCooldownRepository
from src.bot.types import KaguneType
from src.bot.utils import (
    calculate_kagune,
    format_duration,
    get_hunger_tier,
    health_regen_per_hour,
    hours_until_full_health,
)
from src.database.models import Cooldown, Ghoul

from .conftest import (
    button_data,
    callback_update,
    chat_dict,
    message_update,
    owner_dict,
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
        assert await send("пить кофе", uid=UID) == [
            "Ты не гуль. Используй команду 'Растить кагуне' чтобы стать гулем."
        ]

    async def test_grow_kagune_bypasses_even_without_a_ghoul(self, send):
        # миддлварь не блокирует апдейт хинтом "ты не гуль" — доходит до хендлера
        # регистрации (подробно проверяется в TestUpgradeKagune)
        (reply,) = await send("растить кагуне", uid=UID)
        assert reply.startswith("Рождение нового гуля")

    async def test_dead_ghoul_is_blocked(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, is_dead=True)

        assert await send("пить кофе", uid=UID) == [
            "Да ты сдох, что ты собираешься использовать?."
        ]

    async def test_alive_ghoul_reaches_the_handler(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=0)

        # snap_count=0 < COFFEE_CONFIG.snap_limit: до хендлера дошло, просто отказ
        # по другой причине (не хинт "ты не гуль")
        assert await send("пить кофе", uid=UID) == [
            "Бесплатное кофе не дают бездарям. У тебя еще нет сотни сломанных "
            "пальцев, чтобы пить кофе."
        ]


class TestCoffee:
    async def test_below_snap_limit_is_refused(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=0)

        assert await send("пить кофе", uid=UID) == [
            "Бесплатное кофе не дают бездарям. У тебя еще нет сотни сломанных "
            "пальцев, чтобы пить кофе."
        ]

    async def test_accepts_without_gif_when_folder_is_empty(
        self, send, session_factory, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=100, coffee_count=0)
        await seed_cooldown_type(session_factory, "COFFEE", duration=1800)

        (reply,) = await send("пить кофе", uid=UID)

        assert reply.startswith("☕️ Ты выпил чашечку кофе.")
        assert "Всего выпито кофе: 1" in reply

        user = await get_user(session_factory, UID)
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
        assert body["caption"].startswith("☕️ Ты выпил чашечку кофе.")
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
        assert first.startswith("☕️")
        balance_after_first = await balance_of(session_factory, UID)

        # повторный клик во время кулдауна COFFEE: рефанд + переход на COFFEE_DAY
        (second,) = await send("пить кофе", uid=UID)
        assert "передозировку кофе" in second
        balance_after_second = await balance_of(session_factory, UID)
        assert balance_after_second < balance_after_first

        # третий клик — уже под COFFEE_DAY: тот же ответ, но без повторного рефанда
        (third,) = await send("пить кофе", uid=UID)
        assert "передозировку кофе" in third
        balance_after_third = await balance_of(session_factory, UID)
        assert balance_after_third == balance_after_second


class TestUpgradeKagune:
    async def test_creates_ghoul_when_none_exists(self, send, session_factory):
        await seed(session_factory, UID, "Вася")

        (reply,) = await send("растить кагуне", uid=UID)

        assert reply.startswith("Рождение нового гуля")
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

        assert reply.startswith("🐣 Вау, отныне ты гуль... Снова.")
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

        assert "Вышел нахуй отсюда" in reply

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

        assert reply.startswith("✅ Ты успешно усилил свое кагуне.")
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

        assert "не хватает" in reply
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
        assert "Какое кагуне усилить?" in body["text"]
        assert button_data(body, "Укаку - 150 CheSton") == f"kagune_upgrade:{UID}:ukaku"
        assert (
            button_data(body, "Коукаку - 150 CheSton")
            == f"kagune_upgrade:{UID}:koukaku"
        )


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
        assert body["text"].startswith("✅ Ты успешно усилил свое кагуне.")

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.kagune_strength_ukaku == 2

    async def test_wrong_invoker_press_is_silently_ignored(
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

        # pressed_by("invoker_id") не пропускает чужое нажатие ни в один хендлер —
        # апдейт просто ни на что не отвечает
        assert telegram.calls == []

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.kagune_strength_ukaku == 1

    async def test_cooldown_between_keyboard_and_press_gives_alert(
        self, feed, telegram, session_factory
    ):
        await self._seed_two_types(session_factory)
        await seed_active_cooldown(session_factory, UID, "KAGUNE_UPGRADE")

        telegram = await feed(callback_update(f"kagune_upgrade:{UID}:ukaku", uid=UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert "Вышел нахуй отсюда" in answer["text"]
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

        assert reply.startswith("☑️ Пальчик успешно сломан")
        assert "Всего сломано пальцев: 1" in reply
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

        assert "Пальцы еще не перезарядились" in reply
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.snap_count == 0


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

        assert reply.startswith("Топ 20 самых сломанных пальцев")
        assert reply.index("Петя") < reply.index("Вася")  # больше щелчков — выше

    async def test_explicit_count(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, snap_count=1)

        (reply,) = await send("топ щелк 3", uid=UID)

        assert reply.startswith("Топ 3 самых сломанных пальцев")

    async def test_non_digit_count(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        (reply,) = await send("топ щелк абв", uid=UID)

        assert reply == "Топ нужно указывать положительной цифрой"

    async def test_count_out_of_range(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        (reply,) = await send("топ щелк 51", uid=UID)

        assert reply == "Топ не может выходить за пределы значений 1-50"

    @pytest.mark.parametrize(
        ("text", "reply"),
        [
            # как у прода (isdigit): отрицательное — "не цифра", а 0 — вне диапазона
            ("топ щелк -5", "Топ нужно указывать положительной цифрой"),
            ("топ щелк 0", "Топ не может выходить за пределы значений 1-50"),
            ("Топ Щелк 2 лишнее", None),  # регистр и хвост после числа не мешают
        ],
    )
    async def test_count_edge_cases(self, send, session_factory, text, reply):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        (answer,) = await send(text, uid=UID)

        if reply is None:
            assert answer.startswith("Топ 2 самых сломанных пальцев")
        else:
            assert answer == reply

    async def test_longer_word_is_not_a_command(self, send, session_factory):
        # исправленный прод-баг: "топ щелкает" ловилось по началу текста и падало
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        assert await send("топ щелкает", uid=UID) == []


class TestTopKagune:
    async def test_count_errors_like_top_snap(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        assert await send("топ кагуне абв", uid=UID) == [
            "Топ нужно указывать положительной цифрой"
        ]
        assert await send("топ кагуне 99", uid=UID) == [
            "Топ не может выходить за пределы значений 1-50"
        ]

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
        assert body["text"].startswith("Топ 20 самых сильных кагуне в сумме")
        assert "Вася - 7" in body["text"]
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
        assert edited["text"].startswith("Топ 20 самых сильных кагуне: Укаку")
        assert "Вася - 7" in edited["text"]
        assert button_data(edited, "⬅️ Сумма") is not None

    async def test_malformed_callback_data(self, feed, telegram, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        result = await feed(
            callback_update("topkagune:not_a_number:sum:ukaku", uid=UID)
        )

        (answer,) = result.bodies("answerCallbackQuery")
        assert answer["text"] == "Неверные данные кнопки"
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
        assert answer["text"] == "Невозможно обработать запрос"


def group_callback_update(data: str, uid: int, chat: int = -100500) -> dict:
    """Нажатие кнопки под сообщением в группе (callback_update — всегда личка)."""
    update = callback_update(data, uid=uid)
    update["callback_query"]["message"]["chat"] = chat_dict(chat)
    return update


class TestUpgradeStat:
    async def test_group_is_refused(self, send, telegram, session_factory):
        telegram.results["getChatAdministrators"] = [owner_dict(99)]
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        assert await send("качаться", uid=UID, chat=-100500) == [
            "Эта команда работает только в личных сообщениях с ботом."
        ]

    async def test_shop_text_and_buttons(self, feed, session_factory):
        await seed(session_factory, UID, "Вася", balance=12345)
        await seed_ghoul(session_factory, UID, strength=1, level=1)

        telegram = await feed(message_update("Качаться", uid=UID))

        (body,) = telegram.bodies("sendMessage")
        lines = body["text"].split("\n")
        assert lines[0] == "Баланс: 12345"
        price5 = STAT_UPGRADE_CONFIG.price(1, 5, "strength")
        price10 = STAT_UPGRADE_CONFIG.price(1, 10, "strength")
        assert lines[2] == f"💪Сила: 1  х5: {price5} х10: {price10}"
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
        assert f"💪Сила: 98  х5: {price2} х10: {price2}" in body["text"]
        assert button_data(body, f"💪 +5 ({price2})") == "stat_buy:strength:5"

        await seed_ghoul(session_factory, UID, strength=100)
        telegram = await feed(message_update("качаться", uid=UID))
        (body,) = telegram.bodies("sendMessage")
        assert "💪Сила: 100  х5: — х10: —" in body["text"]
        assert button_data(body, "💪 +1 (—)") == "stat_nop"

    async def test_buy_edits_shop_and_answers(self, feed, session_factory):
        await seed(session_factory, UID, "Вася", balance=100000)
        await seed_ghoul(session_factory, UID, strength=1, level=1)
        price = STAT_UPGRADE_CONFIG.price(1, 5, "strength")

        telegram = await feed(callback_update("stat_buy:strength:5", uid=UID))

        (edited,) = telegram.bodies("editMessageText")
        assert edited["text"].startswith(f"Баланс: {100000 - price}")
        assert "💪Сила: 6 " in edited["text"]
        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == f"Прокачано 💪Сила +5. Потрачено: {price}"

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
        assert answer["text"] == f"Прокачано 💪Сила +2. Потрачено: {price}"

    async def test_not_enough_money(self, feed, session_factory):
        await seed(session_factory, UID, "Вася", balance=0)
        await seed_ghoul(session_factory, UID, strength=1, level=1)

        telegram = await feed(callback_update("stat_buy:strength:1", uid=UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Недостаточно средств"
        assert telegram.methods_called("editMessageText") == 0
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.strength == 1

    async def test_buy_at_cap(self, feed, session_factory):
        await seed(session_factory, UID, "Вася", balance=100000)
        await seed_ghoul(session_factory, UID, strength=100, level=1)

        telegram = await feed(callback_update("stat_buy:strength:1", uid=UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Достигнут предел прокачки для этого стата."
        assert await balance_of(session_factory, UID) == 100000

    async def test_nop_button(self, feed, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        telegram = await feed(callback_update("stat_nop", uid=UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Достигнут предел прокачки для этого стата."

    @pytest.mark.parametrize("data", ["stat_nop", "stat_buy:strength:1"])
    async def test_press_in_group_is_refused(self, feed, session_factory, data):
        await seed(session_factory, UID, "Вася", balance=100000)
        await seed_ghoul(session_factory, UID, strength=1, level=1)

        telegram = await feed(group_callback_update(data, uid=UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Эта операция доступна только в личных сообщениях."
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.strength == 1


class TestRegenStatus:
    async def test_full_health(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, health=5, max_health=5)

        (reply,) = await send("Реген", uid=UID)

        assert reply.startswith("❤️ Здоровье: 5/5\n")
        assert reply.endswith("🕰 Уже полностью здоров(а).")

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
        assert f"Скорость регенерации сейчас: {round(per_hour, 2)} HP/ч" in reply
        hours = hours_until_full_health(1, 500, per_hour)
        assert hours is not None
        assert reply.endswith(
            f"До полного здоровья: {format_duration(int(hours * 3600))}"
        )

    async def test_zero_regeneration_never_heals(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, health=1, max_health=500, regeneration=0)

        (reply,) = await send("реген", uid=UID)

        assert reply.endswith(
            "При текущей скорости регенерации здоровье само не восстановится."
        )


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
        assert reply.startswith(f"🍖 Голод: 80% ({tier.name})\n🕰 До истощения: ")
        assert f"сейчас: ×{tier.falling_multiplier}\n" in reply
        assert f"сейчас: ×{tier.rising_multiplier}\n" in reply
        assert "🤟 Сила: " in reply and "♦️ Кагуне: " in reply

    async def test_starved(self, send, session_factory):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, hunger=0)

        (reply,) = await send("голод", uid=UID)

        assert "🕰 Голод уже на нуле.\n" in reply


class FakeQuiz:
    """Вместо QuizService: внешний API в тестах недоступен."""

    def __init__(self, options: list[str], answer: str) -> None:
        self.question = Question(
            id=17, question="Кто?", answer_options=options, answer_group="g"
        )
        self.answer = Answer(
            id=17, question="Кто?", answer=answer, answer_group="g"
        )

    async def get_random_quiz(self) -> Question:
        return self.question

    async def get_answer_by_id(self, question_id: int) -> Answer:
        assert question_id == self.question.id
        return self.answer


def keyboard_callback(body: dict, label: str, uid: int) -> dict:
    """Нажатие кнопки label под сообщением body, с клавиатурой этого сообщения."""
    update = callback_update(button_data(body, label), uid=uid)
    update["callback_query"]["message"]["reply_markup"] = body["reply_markup"]
    return update


class TestQuiz:
    OPTIONS = ["Канеки", "Тоука", "Хинами", "Ута"]

    @pytest.fixture
    def quiz(self, dispatcher, monkeypatch) -> FakeQuiz:
        fake = FakeQuiz(self.OPTIONS, answer="Канеки")
        monkeypatch.setattr(dispatcher, "quiz_service", fake)
        return fake

    async def _ask(self, feed, session_factory, uid: int = UID) -> dict:
        await seed(session_factory, uid, "Вася")
        await seed_ghoul(session_factory, uid)
        telegram = await feed(message_update("/quiz", uid=uid))
        (body,) = telegram.bodies("sendMessage")
        return body

    async def test_question_with_four_options_two_per_row(
        self, feed, session_factory, quiz
    ):
        body = await self._ask(feed, session_factory)

        assert body["text"] == "Кто?"
        assert body["reply_parameters"]["message_id"] == 1
        rows = body["reply_markup"]["inline_keyboard"]
        assert [len(row) for row in rows] == [2, 2]
        labels = [b["text"] for row in rows for b in row]
        assert sorted(labels) == sorted(self.OPTIONS)
        assert button_data(body, labels[3]) == "quiz_answer:17:3"

    async def test_correct_answer_pays_and_offers_restart(
        self, feed, session_factory, quiz
    ):
        body = await self._ask(feed, session_factory)

        telegram = await feed(keyboard_callback(body, "Канеки", UID))

        (edited,) = telegram.bodies("editMessageText")
        head, award = edited["text"].split("Получено CheSton: ")
        assert head == (
            "Вопрос: Кто? \nОтвет: Канеки.\nТвой выбор: Канеки\nСтатус: верно\n\n"
        )
        assert await balance_of(session_factory, UID) == int(award)
        assert button_data(edited, "Play Again") == "quiz_restart"
        # как у прода: часики на кнопке не закрываются
        assert telegram.methods_called("answerCallbackQuery") == 0

    async def test_wrong_answer(self, feed, session_factory, quiz):
        body = await self._ask(feed, session_factory)

        telegram = await feed(keyboard_callback(body, "Тоука", UID))

        (edited,) = telegram.bodies("editMessageText")
        assert edited["text"] == (
            "Вопрос: Кто? \nОтвет: Канеки.\nТвой выбор: Тоука\nСтатус: неверно"
        )
        assert await balance_of(session_factory, UID) == 0

    async def test_second_answer_is_not_active(self, feed, session_factory, quiz):
        body = await self._ask(feed, session_factory)
        await feed(keyboard_callback(body, "Тоука", UID))

        telegram = await feed(keyboard_callback(body, "Канеки", UID))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Quiz is not active."
        assert await balance_of(session_factory, UID) == 0

    async def test_someone_elses_quiz_is_not_active(self, feed, session_factory, quiz):
        body = await self._ask(feed, session_factory)
        await seed(session_factory, UID + 1, "Петя")
        await seed_ghoul(session_factory, UID + 1)

        telegram = await feed(keyboard_callback(body, "Канеки", UID + 1))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Quiz is not active."

    async def test_play_again_asks_a_new_question(self, feed, session_factory, quiz):
        body = await self._ask(feed, session_factory)
        telegram = await feed(keyboard_callback(body, "Тоука", UID))
        (edited,) = telegram.bodies("editMessageText")

        telegram = await feed(keyboard_callback(edited, "Play Again", UID))

        (question,) = telegram.bodies("editMessageText")
        assert question["text"] == "Кто?"
        telegram = await feed(keyboard_callback(question, "Канеки", UID))
        (result,) = telegram.bodies("editMessageText")
        assert "Статус: верно" in result["text"]

    async def test_long_option_fits_the_button(
        self, feed, session_factory, dispatcher, monkeypatch
    ):
        # у прода текст варианта едет в callback_data и такой вопрос не отправить
        long = "Кен Канеки после встречи с Ризе Камиширо"
        fake = FakeQuiz([long, "а_б", "в", "г"], answer=long)
        monkeypatch.setattr(dispatcher, "quiz_service", fake)
        body = await self._ask(feed, session_factory)

        telegram = await feed(keyboard_callback(body, long, UID))

        (edited,) = telegram.bodies("editMessageText")
        assert f"Твой выбор: {long}\nСтатус: верно" in edited["text"]


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
        assert blocks[0]["text"].startswith("⚡ Боевая мощь гуля ")
        assert blocks[0]["text"].endswith(" ранга Вася ")
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

        assert reply.startswith("⚡ Боевая мощь гуля ")
        assert "\n\n🤟 Сила: 10 → " in reply
        assert "\n❤️ Здоровье: 50 → " in reply
        assert "\n♦️ Кагуне: 4 → " in reply
        assert reply.endswith("используй /kagune.")

    async def test_short_alias(self, send, session_factory):
        ghoul = await self._seed(session_factory)
        power = sum(
            (ghoul.strength, ghoul.dexterity, ghoul.speed, ghoul.max_health)
        ) + (ghoul.regeneration + 4)  # + сила кагуне

        (reply,) = await send("БМ", uid=UID)

        vacuum, effective = reply.split("\n")
        assert vacuum == f"Твоя боевая мощь вне боя: {power}"
        assert effective.startswith("Твоя боевая мощь в бою: ")
