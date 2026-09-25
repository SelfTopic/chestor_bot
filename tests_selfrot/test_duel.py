"""routers/ghoul_routers/duel: приглашение (ответом и по @username/id), согласие,
"всерьёз/фора", бой, выбор победителя и таймауты DuelTicker.

Исход боя без случайности: у B нулевая сила, он не может ранить A, а мощь у обоих
одинаковая (перевес 1 < порога 2, шаг "фора" пропускается). Для шага "фора" A
вдвое мощнее B."""

import asyncio
import json
from typing import Any

import pytest

from src.bot.repositories import (
    ActiveBattleRepository,
    BattleRepository,
    DuelSessionRepository,
)
from src.bot.services.battle_record import BattleRecordService
from src.database.models import DuelSession

from .conftest import button_data, callback_update, message_update, owner_dict
from .test_common_routers import seed
from .test_ghoul_battles import is_busy
from .test_ghoul_routers import balance_of, get_ghoul, seed_ghoul

A, B, C = 700001, 700002, 700003
GROUP = -100500

# Мощь (сумма статов) у обоих 221; B не наносит урона.
WINNER: dict[str, Any] = dict(
    strength=100, dexterity=10, speed=10, health=100, max_health=100, regeneration=1
)
HARMLESS: dict[str, Any] = dict(
    strength=0, dexterity=101, speed=10, health=100, max_health=100, regeneration=10
)
# Вдвое мощнее HARMLESS: выбор "всерьёз/фора" достаётся A.
FAVORED: dict[str, Any] = dict(
    strength=300, dexterity=50, speed=50, health=100, max_health=100
)


async def seed_duelist(
    session_factory, uid: int, name: str, private: bool = True, **ghoul: Any
) -> None:
    await seed(session_factory, uid, name, has_private_chat=private)
    await seed_ghoul(session_factory, uid, hunger=100, **ghoul)


async def active_duel(session_factory, uid: int = A) -> DuelSession | None:
    async with session_factory() as session:
        return await DuelSessionRepository(session).find_active_for(uid)


async def get_duel(session_factory, duel_id: int) -> DuelSession:
    async with session_factory() as session:
        duel = await DuelSessionRepository(session).get(duel_id)
    assert duel is not None
    return duel


async def record_duels(session_factory, a: int, b: int, count: int) -> None:
    async with session_factory() as session:
        service = BattleRecordService(
            ActiveBattleRepository(session), BattleRepository(session)
        )
        for _ in range(count):
            await service.record_duel(a, b, winner="a", ended_naturally=True)
        await session.commit()


NAMES = {A: "Вася", B: "Петя", C: "Коля"}


def press(duel_id: int, action: str, expected: int, uid: int | None = None) -> dict:
    """Нажатие кнопки дуэли; имя нажавшего своё (SyncEntities обновляет его в БД)."""
    uid = expected if uid is None else uid
    update = callback_update(f"duel:{duel_id}:{action}:{expected}", uid=uid)
    update["callback_query"]["from"]["first_name"] = NAMES[uid]
    return update


def rich_text(body: dict) -> str:
    return json.dumps(body["rich_message"], ensure_ascii=False)


@pytest.fixture(autouse=True)
def group_admins(telegram):
    telegram.results["getChatAdministrators"] = [owner_dict(99)]


@pytest.fixture
def invite(feed):
    """Вызов A → B ответом в группе; возвращает id созданной дуэли."""

    async def _invite(session_factory) -> int:
        await feed(message_update("дуэль", uid=A, chat=GROUP, reply_to_uid=B))
        duel = await active_duel(session_factory)
        assert duel is not None
        return duel.id

    return _invite


class TestInvite:
    async def test_usage_without_target(self, send, session_factory):
        await seed_duelist(session_factory, A, "Вася")

        assert await send("Дуэль", uid=A, chat=GROUP) == [
            "Вызови реплаем на сообщение соперника, либо «дуэль @username» / "
            "«дуэль <id>»."
        ]

    async def test_startswith_quirk(self, send, session_factory):
        # как у прода: команда ловится по началу текста
        await seed_duelist(session_factory, A, "Вася")

        assert await send("дуэльный вызов", uid=A, chat=GROUP) == [
            "Пользователь не найден: вызов"
        ]

    async def test_unknown_username(self, send, session_factory):
        await seed_duelist(session_factory, A, "Вася")

        assert await send("дуэль @nobody", uid=A, chat=GROUP) == [
            "Пользователь не найден: @nobody"
        ]

    async def test_self(self, send, session_factory):
        await seed_duelist(session_factory, A, "Вася")

        assert await send(
            "дуэль", uid=A, chat=GROUP, reply_to_uid=A, reply_to_name="Вася"
        ) == ["Нельзя вызвать на дуэль самого себя."]

    async def test_unregistered_target(self, send, session_factory):
        await seed_duelist(session_factory, A, "Вася")

        assert await send("дуэль", uid=A, chat=GROUP, reply_to_uid=B) == [
            "Один из участников не зарегистрирован."
        ]

    @pytest.mark.parametrize(
        ("initiator_private", "who"), [(False, "Тебе"), (True, "Сопернику")]
    )
    async def test_private_chat_required(
        self, send, session_factory, initiator_private, who
    ):
        await seed_duelist(session_factory, A, "Вася", private=initiator_private)
        await seed_duelist(session_factory, B, "Петя", private=False)

        assert await send("дуэль", uid=A, chat=GROUP, reply_to_uid=B) == [
            f"{who} нужно один раз написать боту в ЛС (подойдёт /start) - иначе "
            "часть сообщений о бое некуда будет доставить."
        ]

    async def test_target_without_ghoul(self, send, session_factory):
        await seed_duelist(session_factory, A, "Вася")
        await seed(session_factory, B, "Петя", has_private_chat=True)

        assert await send("дуэль", uid=A, chat=GROUP, reply_to_uid=B) == [
            "У соперника ещё нет гуля."
        ]

    @pytest.mark.parametrize(
        ("target", "reply"),
        [
            ({"is_dead": True}, "Один из участников мёртв."),
            (
                {"health": 4},
                "Один из участников небоеспособен: 4 HP (нужно минимум 5).",
            ),
        ],
    )
    async def test_target_cannot_fight(self, send, session_factory, target, reply):
        await seed_duelist(session_factory, A, "Вася", **WINNER)
        await seed_duelist(session_factory, B, "Петя", **{**HARMLESS, **target})

        assert await send("дуэль", uid=A, chat=GROUP, reply_to_uid=B) == [reply]

    async def test_busy_target(self, send, session_factory):
        await seed_duelist(session_factory, A, "Вася", **WINNER)
        await seed_duelist(session_factory, B, "Петя", **HARMLESS)
        await seed_duelist(session_factory, C, "Коля", **HARMLESS)
        await send("дуэль", uid=C, chat=GROUP, reply_to_uid=B)

        assert await send("дуэль", uid=A, chat=GROUP, reply_to_uid=B) == [
            "Один из участников уже занят другим боем."
        ]

    async def test_pair_limit(self, send, session_factory):
        await seed_duelist(session_factory, A, "Вася", **WINNER)
        await seed_duelist(session_factory, B, "Петя", **HARMLESS)
        await record_duels(session_factory, A, B, 5)

        assert await send("дуэль", uid=A, chat=GROUP, reply_to_uid=B) == [
            "Лимит боёв с этим соперником на сегодня исчерпан (5/сутки)."
        ]

    async def test_daily_limit(self, send, session_factory):
        await seed_duelist(session_factory, A, "Вася", **WINNER)
        await seed_duelist(session_factory, B, "Петя", **HARMLESS)
        await seed(session_factory, C, "Коля")
        await record_duels(session_factory, A, C, 20)

        assert await send("дуэль", uid=A, chat=GROUP, reply_to_uid=B) == [
            "Твой дневной лимит боёв исчерпан (20/сутки)."
        ]

    async def test_target_daily_limit(self, send, session_factory):
        await seed_duelist(session_factory, A, "Вася", **WINNER)
        await seed_duelist(session_factory, B, "Петя", **HARMLESS)
        await seed(session_factory, C, "Коля")
        await record_duels(session_factory, B, C, 20)

        assert await send("дуэль", uid=A, chat=GROUP, reply_to_uid=B) == [
            "У соперника исчерпан дневной лимит боёв на сегодня."
        ]

    async def test_group_invite(self, feed, session_factory):
        await seed_duelist(session_factory, A, "Вася", **WINNER)
        await seed_duelist(session_factory, B, "Петя", **HARMLESS)

        telegram = await feed(
            message_update("дуэль", uid=A, chat=GROUP, reply_to_uid=B)
        )

        (body,) = telegram.bodies("sendMessage")
        assert body["chat_id"] == GROUP
        # у БД-пользователя без фамилии full_name с пробелом на конце, как у прода
        assert body["text"] == (
            "⚔️ Вася  вызывает Петя  на дуэль!\n"
            "Бой начнётся только после подтверждения ОБЕИХ сторон."
        )
        duel = await active_duel(session_factory)
        assert duel is not None and not duel.is_private_origin
        assert duel.consent_message_id == 100
        assert (
            button_data(body, "✅ Подтверждаю вызов (инициатор)")
            == f"duel:{duel.id}:consent_initiator:{A}"
        )
        assert (
            button_data(body, "⚔️ Принимаю бой") == f"duel:{duel.id}:consent_target:{B}"
        )
        assert await is_busy(session_factory, A) and await is_busy(session_factory, B)

    async def test_private_origin_invite_goes_to_both(self, feed, session_factory):
        await seed_duelist(session_factory, A, "Вася", **WINNER)
        await seed(session_factory, B, "Петя", username="petya", has_private_chat=True)
        await seed_ghoul(session_factory, B, hunger=100, **HARMLESS)

        telegram = await feed(message_update("дуэль @petya", uid=A))

        assert [b["chat_id"] for b in telegram.bodies("sendMessage")] == [A, B]
        duel = await active_duel(session_factory)
        assert duel is not None and duel.is_private_origin
        assert duel.consent_message_id is None

    async def test_explicit_id(self, feed, session_factory):
        await seed_duelist(session_factory, A, "Вася", **WINNER)
        await seed_duelist(session_factory, B, "Петя", **HARMLESS)

        await feed(message_update(f"дуэль {B}", uid=A, chat=GROUP))

        duel = await active_duel(session_factory)
        assert duel is not None and duel.target_telegram_id == B


class TestConsent:
    async def _seed(self, session_factory, a=WINNER, b=HARMLESS) -> None:
        await seed_duelist(session_factory, A, "Вася", **a)
        await seed_duelist(session_factory, B, "Петя", **b)

    async def test_someone_elses_button(self, feed, session_factory, invite):
        await self._seed(session_factory)
        duel_id = await invite(session_factory)

        telegram = await feed(press(duel_id, "consent_target", B, uid=A))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer == {
            "callback_query_id": "cq1",
            "text": "Это не твоя кнопка.",
            "show_alert": True,
        }
        duel = await get_duel(session_factory, duel_id)
        assert not duel.target_consented

    async def test_malformed_button(self, feed, session_factory):
        await self._seed(session_factory)

        telegram = await feed(callback_update("duel:x:consent_target:1", uid=A))

        assert telegram.bodies("answerCallbackQuery") == [{"callback_query_id": "cq1"}]

    async def test_first_consent_waits_for_second(self, feed, session_factory, invite):
        await self._seed(session_factory)
        duel_id = await invite(session_factory)

        telegram = await feed(press(duel_id, "consent_target", B))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Принято, ждём второго участника."
        (edited,) = telegram.bodies("editMessageText")
        assert edited["chat_id"] == GROUP and edited["message_id"] == 100
        assert edited["text"] == "✅ Один из участников подтвердил, ждём второго."
        assert button_data(edited, "⚔️ Принимаю бой")

    async def test_both_consent_runs_the_fight(self, feed, session_factory, invite):
        await self._seed(session_factory)
        duel_id = await invite(session_factory)
        await feed(press(duel_id, "consent_target", B))

        telegram = await feed(press(duel_id, "consent_initiator", A))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Оба подтвердили!"
        assert telegram.bodies("deleteMessage") == [
            {"chat_id": GROUP, "message_id": 100}
        ]
        (rich,) = telegram.bodies("sendRichMessage")
        assert rich["chat_id"] == GROUP
        assert "🏆 Победитель: " in rich_text(rich) and "Вася" in rich_text(rich)
        assert button_data(rich, "🕊️ Отпустить") == f"duel:{duel_id}:outcome_release:{A}"

        duel = await get_duel(session_factory, duel_id)
        assert duel.stage == "awaiting_winner_choice"
        assert (duel.winner_telegram_id, duel.loser_telegram_id) == (A, B)
        assert duel.compress_hp is True and duel.outcome_message_id == 100
        winner = await get_ghoul(session_factory, A)
        assert winner is not None and winner.level_progress == pytest.approx(1.0)

    async def test_consent_after_the_invite_ended(self, feed, session_factory, invite):
        await self._seed(session_factory)
        duel_id = await invite(session_factory)
        await feed(press(duel_id, "consent_target", B))
        await feed(press(duel_id, "consent_initiator", A))

        telegram = await feed(press(duel_id, "consent_target", B))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Приглашение уже неактуально."
        assert answer["show_alert"] is True

    async def test_plain_text_when_rich_fails(
        self, feed, telegram, session_factory, invite
    ):
        await self._seed(session_factory)
        duel_id = await invite(session_factory)
        await feed(press(duel_id, "consent_target", B))
        telegram.errors["sendRichMessage"] = (400, "Bad Request: rich not supported")

        telegram = await feed(press(duel_id, "consent_initiator", A))

        (body,) = telegram.bodies("sendMessage")
        assert body["text"].startswith("⚔️ Бой\n\nГуль ")
        assert button_data(body, "💰 Ограбить") == f"duel:{duel_id}:outcome_rob:{A}"

    async def test_much_stronger_side_chooses(self, feed, session_factory, invite):
        await self._seed(session_factory, a=FAVORED)
        duel_id = await invite(session_factory)
        await feed(press(duel_id, "consent_target", B))

        telegram = await feed(press(duel_id, "consent_initiator", A))

        group, dm = telegram.bodies("sendMessage")
        assert group["chat_id"] == GROUP
        assert group["text"] == "⚔️ Оба согласились! Ждём решения сильнейшей стороны."
        assert dm["chat_id"] == A
        assert dm["text"] == (
            "Ты значительно сильнее соперника. Драться всерьёз или дать фору?"
        )
        assert button_data(dm, "🤝 Дать фору") == f"duel:{duel_id}:fora_handicap:{A}"
        assert telegram.methods_called("sendRichMessage") == 0
        duel = await get_duel(session_factory, duel_id)
        assert duel.stage == "awaiting_serious_or_handicap"
        assert duel.favored_telegram_id == A

    @pytest.mark.parametrize(
        ("action", "compress"), [("fora_serious", False), ("fora_handicap", True)]
    )
    async def test_fora_choice_runs_the_fight(
        self, feed, session_factory, invite, action, compress
    ):
        await self._seed(session_factory, a=FAVORED)
        duel_id = await invite(session_factory)
        await feed(press(duel_id, "consent_target", B))
        await feed(press(duel_id, "consent_initiator", A))

        telegram = await feed(press(duel_id, action, A))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Принято!"
        (edited,) = telegram.bodies("editMessageText")
        assert edited["text"] == "Решение принято, бой начинается."
        assert telegram.methods_called("sendRichMessage") == 1
        duel = await get_duel(session_factory, duel_id)
        assert duel.compress_hp is compress
        assert duel.stage == "awaiting_winner_choice"

        telegram = await feed(press(duel_id, action, A))
        (late,) = telegram.bodies("answerCallbackQuery")
        assert late["text"] == "Уже неактуально."


class TestOutcome:
    @pytest.fixture
    async def fought(self, feed, session_factory, invite) -> int:
        await seed_duelist(session_factory, A, "Вася", **WINNER)
        await seed_duelist(session_factory, B, "Петя", **HARMLESS)
        duel_id = await invite(session_factory)
        await feed(press(duel_id, "consent_target", B))
        await feed(press(duel_id, "consent_initiator", A))
        return duel_id

    async def test_release(self, feed, session_factory, fought):
        telegram = await feed(press(fought, "outcome_release", A))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Принято!"
        assert telegram.bodies("editMessageReplyMarkup") == [
            {"chat_id": GROUP, "message_id": 100}
        ]
        sent = telegram.bodies("sendMessage")
        assert sorted(b["chat_id"] for b in sent) == sorted([A, B, GROUP])
        assert sent[0]["text"] == (
            "🕊️ Вася  решил отпустить Петя .\n\n"
            "📈 Вася  получил 1.00% опыта за победу.\n\n"
            "📊 Вася : 1 боёв (1П/0)\n📊 Петя : 1 боёв (0П/1)"
        )
        duel = await get_duel(session_factory, fought)
        assert duel.stage == "done" and duel.winner_choice == "outcome_release"
        assert not await is_busy(session_factory, A)
        assert not await is_busy(session_factory, B)

        telegram = await feed(press(fought, "outcome_rob", A))
        (late,) = telegram.bodies("answerCallbackQuery")
        assert late["text"] == "Уже неактуально."

    async def test_rob(self, feed, session_factory, fought):
        async with session_factory() as session:
            from src.bot.repositories import UserRepository

            await UserRepository(session).change_data(B, balance=1000)
            await session.commit()

        telegram = await feed(press(fought, "outcome_rob", A))

        taken = await balance_of(session_factory, A)
        assert 100 <= taken <= 250
        assert await balance_of(session_factory, B) == 1000 - taken
        assert telegram.bodies("sendMessage")[0]["text"].startswith(
            f"💰 Вася  ограбил Петя  и забрал {taken} CheSton's!"
        )

    async def test_rob_a_broke_loser(self, feed, session_factory, fought):
        telegram = await feed(press(fought, "outcome_rob", A))

        assert telegram.bodies("sendMessage")[0]["text"].startswith(
            "💰 Вася  попытался ограбить Петя , но у тот оказался ебаный бомж "
            "и у нечего взять."
        )

    async def test_eat(self, feed, session_factory, fought):
        telegram = await feed(press(fought, "outcome_eat", A))

        loser = await get_ghoul(session_factory, B)
        assert loser is not None and loser.is_dead
        winner = await get_ghoul(session_factory, A)
        assert winner is not None and winner.eat_ghouls == 1 and winner.rc_money > 0
        text = telegram.bodies("sendMessage")[0]["text"]
        assert text.startswith(
            f"🍖 Вася  нещадно добил и сожрал Петя , получив {winner.rc_money} "
            "RC-клеток\n🍖 Голод Вася  восстановлен на "
        )

    async def test_loser_cannot_choose(self, feed, session_factory, fought):
        telegram = await feed(press(fought, "outcome_release", A, uid=B))

        (answer,) = telegram.bodies("answerCallbackQuery")
        assert answer["text"] == "Это не твоя кнопка."


class TestDraw:
    async def test_draw_is_recorded_at_once(self, feed, session_factory, invite):
        await seed_duelist(session_factory, A, "Вася", **HARMLESS)
        await seed_duelist(session_factory, B, "Петя", **HARMLESS)
        duel_id = await invite(session_factory)
        await feed(press(duel_id, "consent_target", B))

        telegram = await feed(press(duel_id, "consent_initiator", A))

        (rich,) = telegram.bodies("sendRichMessage")
        assert "🤝 Ничья." in rich_text(rich)
        assert "reply_markup" not in rich
        duel = await get_duel(session_factory, duel_id)
        assert duel.stage == "done"
        assert not await is_busy(session_factory, A)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class TestTicker:
    @pytest.fixture
    def clock(self, dispatcher) -> FakeClock:
        clock = FakeClock()
        dispatcher.duel_ticker.clock = clock
        return clock

    @pytest.fixture
    def tick(self, dispatcher, telegram, clock):
        """Тик через seconds секунд после предыдущего; вызовы Telegram — только его."""

        async def _tick(seconds: float = 0):
            clock.now += seconds
            telegram.calls.clear()
            await dispatcher.duel_ticker.tick()
            return telegram

        return _tick

    async def _seed(self, session_factory, a=WINNER) -> None:
        await seed_duelist(session_factory, A, "Вася", **a)
        await seed_duelist(session_factory, B, "Петя", **HARMLESS)

    async def test_consent_timeout(self, session_factory, invite, tick):
        await self._seed(session_factory)
        duel_id = await invite(session_factory)
        await tick()  # тикер впервые видит дуэль

        telegram = await tick(59)
        assert telegram.calls == []

        telegram = await tick(1)
        assert telegram.bodies("deleteMessage") == [
            {"chat_id": GROUP, "message_id": 100}
        ]
        sent = telegram.bodies("sendMessage")
        assert sorted(b["chat_id"] for b in sent) == sorted([A, B, GROUP])
        assert {b["text"] for b in sent} == {
            "⌛ Время на согласие вышло - дуэль отменена."
        }
        duel = await get_duel(session_factory, duel_id)
        assert duel.stage == "done"
        assert not await is_busy(session_factory, A)

        telegram = await tick(60)
        assert telegram.calls == []

    async def test_fora_timeout_gives_handicap(
        self, feed, session_factory, invite, tick
    ):
        await self._seed(session_factory, a=FAVORED)
        duel_id = await invite(session_factory)
        await feed(press(duel_id, "consent_target", B))
        await feed(press(duel_id, "consent_initiator", A))
        await tick()

        telegram = await tick(30)

        assert telegram.methods_called("sendRichMessage") == 1
        duel = await get_duel(session_factory, duel_id)
        assert duel.compress_hp is True
        assert duel.stage == "awaiting_winner_choice"

    async def test_outcome_timeout_releases(self, feed, session_factory, invite, tick):
        await self._seed(session_factory)
        duel_id = await invite(session_factory)
        await feed(press(duel_id, "consent_target", B))
        await feed(press(duel_id, "consent_initiator", A))
        await tick()

        telegram = await tick(60)

        assert telegram.bodies("sendMessage")[0]["text"].startswith(
            "🕊️ Вася  решил отпустить Петя ."
        )
        duel = await get_duel(session_factory, duel_id)
        assert duel.stage == "done" and duel.winner_choice == "outcome_release"
        assert not await is_busy(session_factory, B)

    async def test_countdown_restarts_on_the_next_stage(
        self, feed, session_factory, invite, tick
    ):
        await self._seed(session_factory)
        duel_id = await invite(session_factory)
        await tick()
        await tick(50)
        await feed(press(duel_id, "consent_target", B))
        await feed(press(duel_id, "consent_initiator", A))

        await tick(20)  # 70 с после приглашения, но стадия выбора только началась
        duel = await get_duel(session_factory, duel_id)
        assert duel.stage == "awaiting_winner_choice"

    async def test_start_runs_ticks_and_stop_cancels(
        self, dispatcher, session_factory, invite, clock
    ):
        await self._seed(session_factory)
        duel_id = await invite(session_factory)
        ticker = dispatcher.duel_ticker
        ticker._interval = 0.01
        clock.now = -1000.0  # первый тик видит дуэль "давно"; дальше время стоит

        await ticker.start()
        await asyncio.sleep(0.2)
        clock.now = 0.0
        await asyncio.sleep(0.2)
        await ticker.stop()

        duel = await get_duel(session_factory, duel_id)
        assert duel.stage == "done"
        assert ticker._task is None
