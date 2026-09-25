"""routers/ghoul_routers: GhoulMiddleware гейтит весь роутер (без гуля — молчание с
подсказкой, кроме "растить кагуне"; мёртвому гулю тоже отказ). coffee.py: использует
оба новых ctx-хелпера (reply_gif через media_paths.random_media; кулдаун — не через
ctx.cooldown_remaining, а CoffeeService.execute_cooldown, который сам решает COFFEE
это или COFFEE_DAY, см. coffee.py). upgrade_kagune/: единственная команда, доступная
и без гуля (регистрация), и мёртвому гулю (возрождение) — bypass в GhoulMiddleware;
типизированный KaguneUpgradePress вместо ручного parse_kagune_callback_payload."""

import json

import pytest

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


class TestTopKagune:
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

    async def test_malformed_callback_data_is_silently_ignored(
        self, feed, telegram, session_factory
    ):
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID)

        result = await feed(
            callback_update("topkagune:not_a_number:sum:ukaku", uid=UID)
        )

        assert result.calls == []


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
