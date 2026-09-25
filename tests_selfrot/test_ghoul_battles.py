"""Бои с мобом: "бить моба" (mob_fight.py) и засада в "сожрать человека"
(eat_human.py). Исход боя задаётся подменённым MobService: моб-пустышка (игрок
побеждает), моб-громила (игрок проигрывает) или зеркало без урона (ничья)."""

import json

import pytest
from dependency_injector import providers

from src.bot.config import game_config
from src.bot.game_configs import EAT_HUMAN_CONFIG, MOB_CONFIG
from src.bot.repositories import ActiveBattleRepository, BattleRepository
from src.bot.services.battle_engine.core import FighterSnapshot
from src.bot.services.battle_record import BattleRecordService

from .conftest import message_update
from .test_common_routers import seed
from .test_ghoul_routers import (
    UID,
    balance_of,
    get_ghoul,
    seed_active_cooldown,
    seed_cooldown_type,
    seed_ghoul,
)


class FakeMobService:
    def __init__(self, kind: str) -> None:
        self.kind = kind

    def generate_mob(self, player: FighterSnapshot, rng=None) -> FighterSnapshot:
        stats = {
            "weak": dict(strength=0, dexterity=1, regeneration=0, speed=1, health=1),
            "strong": dict(
                strength=5000, dexterity=500, regeneration=0, speed=500, health=50000
            ),
            "mirror": dict(
                strength=player.strength,
                dexterity=player.dexterity,
                regeneration=player.regeneration,
                speed=player.speed,
                health=player.health,
            ),
        }[self.kind]
        return FighterSnapshot(
            id=-1,
            name="Безумный гуль",
            hunger=100,
            is_kakuja=False,
            kagune_strength={},
            **stats,
        )


# Исходы без случайности: у "weak" нулевая сила, он не может победить сильного
# игрока; игрок с нулевой силой не может победить "strong"; против своего зеркала
# урона нет ни у кого, и бой кончается ничьей по раундам.
STRONG_PLAYER = dict(
    strength=500, dexterity=100, speed=100, health=500, max_health=500, regeneration=1
)
HARMLESS_PLAYER = dict(
    strength=0, dexterity=10, speed=10, health=50, max_health=50, regeneration=0
)


@pytest.fixture
def mob(dispatcher):
    def _set(kind: str) -> None:
        dispatcher.container.mob_service.override(
            providers.Object(FakeMobService(kind))
        )

    return _set


@pytest.fixture(autouse=True)
def no_rc_drop(monkeypatch):
    monkeypatch.setattr(MOB_CONFIG, "rc_drop_chance", 0.0)


async def mob_battles(session_factory, telegram_id: int) -> tuple[int, int, int]:
    async with session_factory() as session:
        service = BattleRecordService(
            ActiveBattleRepository(session), BattleRepository(session)
        )
        return (
            await service.count_total_battles_vs_mobs(telegram_id),
            await service.count_wins_vs_mobs(telegram_id),
            await service.count_losses_vs_mobs(telegram_id),
        )


async def is_busy(session_factory, telegram_id: int) -> bool:
    async with session_factory() as session:
        return await ActiveBattleRepository(session).get(telegram_id) is not None


async def claim_mob_fight(session_factory, telegram_id: int) -> None:
    async with session_factory() as session:
        service = BattleRecordService(
            ActiveBattleRepository(session), BattleRepository(session)
        )
        assert await service.try_claim_mob_fight(telegram_id)
        await session.commit()


class TestMobFight:
    async def _seed(self, session_factory, **ghoul) -> None:
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, **ghoul)
        await seed_cooldown_type(session_factory, "MOB_FIGHT", duration=600)

    async def test_win_pays_and_counts(self, feed, session_factory, mob):
        mob("weak")
        await self._seed(session_factory, **STRONG_PLAYER)

        telegram = await feed(message_update("Бить моба", uid=UID))

        (rich,) = telegram.bodies("sendRichMessage")
        rich_text = json.dumps(rich, ensure_ascii=False)
        assert "⚔️ Бой" in rich_text and "Безумный гуль" in rich_text
        (summary,) = telegram.sent
        lines = summary.split("\n")
        assert lines[0].startswith("📈 Получено опыта: ")
        assert lines[1].startswith("💰 Получено CheSton: ")
        assert lines[2] == "📊 Боёв с мобами: 1 (1 побед / 0 поражений)"

        cheston = int(lines[1].removeprefix("💰 Получено CheSton: "))
        assert await balance_of(session_factory, UID) == cheston
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.level_progress > 0
        assert await mob_battles(session_factory, UID) == (1, 1, 0)
        assert not await is_busy(session_factory, UID)

    async def test_rc_drop_line(self, send, session_factory, mob, monkeypatch):
        monkeypatch.setattr(MOB_CONFIG, "rc_drop_chance", 1.0)
        mob("weak")
        await self._seed(session_factory, **STRONG_PLAYER, rc_money=0)

        (summary,) = await send("бить моба", uid=UID)

        rc_line = summary.split("\n")[2]
        assert rc_line.startswith("♦️ Дополнительно найдено: ")
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and f" {ghoul.rc_money} RC-клеток!" in rc_line

    async def test_loss(self, send, session_factory, mob):
        mob("strong")
        await self._seed(session_factory, **HARMLESS_PLAYER)

        assert await send("бить моба", uid=UID) == [
            "Моб оказался сильнее в этот раз.\n"
            "📊 Боёв с мобами: 1 (0 побед / 1 поражений)"
        ]
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.health == 1  # бой сам не убивает
        assert await balance_of(session_factory, UID) == 0

    async def test_draw(self, send, session_factory, mob):
        mob("mirror")
        await self._seed(session_factory, **HARMLESS_PLAYER)

        assert await send("бить моба", uid=UID) == [
            "Ничья - силы примерно равны.\n📊 Боёв с мобами: 1 (0 побед / 0 поражений)"
        ]

    async def test_plain_text_when_rich_fails(
        self, feed, telegram, session_factory, mob
    ):
        mob("weak")
        await self._seed(session_factory, **STRONG_PLAYER)
        telegram.errors["sendRichMessage"] = (400, "Bad Request: rich not supported")

        sent = (await feed(message_update("бить моба", uid=UID))).sent

        assert len(sent) == 2
        assert sent[0].startswith("⚔️ Бой\n\nГуль ")
        assert "\nVS\n" in sent[0] and "📜 Раундов: " in sent[0]
        assert sent[1].startswith("📈 Получено опыта: ")

    async def test_cooldown(self, send, session_factory, mob):
        mob("weak")
        await self._seed(session_factory, **STRONG_PLAYER)
        await send("бить моба", uid=UID)

        (reply,) = await send("бить моба", uid=UID)

        assert reply.startswith("Рано - ты недавно уже дрался с мобом. Попробуй через ")
        assert await mob_battles(session_factory, UID) == (1, 1, 0)

    async def test_not_combat_ready(self, send, session_factory, mob):
        mob("weak")
        await self._seed(session_factory, **{**STRONG_PLAYER, "health": 4})

        assert await send("бить моба", uid=UID) == [
            "Ты небоеспособен: 4 HP (нужно минимум 5). Дай себе время восстановиться."
        ]

    async def test_busy_with_another_battle(self, send, session_factory, mob):
        mob("weak")
        await self._seed(session_factory, **STRONG_PLAYER)
        await claim_mob_fight(session_factory, UID)

        assert await send("бить моба", uid=UID) == ["Ты сейчас занят другим боем."]
        assert await mob_battles(session_factory, UID) == (0, 0, 0)

    async def test_readiness_is_checked_before_cooldown(
        self, send, session_factory, mob
    ):
        # как у прода: сначала боеготовность, потом кулдаун
        mob("weak")
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, **{**STRONG_PLAYER, "health": 4})
        await seed_active_cooldown(session_factory, UID, "MOB_FIGHT")

        (reply,) = await send("бить моба", uid=UID)

        assert reply.startswith("Ты небоеспособен")


class TestEatHuman:
    @pytest.fixture(autouse=True)
    def assets(self, monkeypatch, tmp_path):
        monkeypatch.setattr(game_config, "path_to_assets", str(tmp_path))
        return tmp_path

    @pytest.fixture
    def ambush(self, monkeypatch):
        def _set(percent: float) -> None:
            monkeypatch.setattr(EAT_HUMAN_CONFIG, "ambush_chance_percent", percent)

        return _set

    async def _seed(self, session_factory, **ghoul) -> None:
        await seed(session_factory, UID, "Вася")
        await seed_ghoul(session_factory, UID, **{"hunger": 10, **ghoul})
        await seed_cooldown_type(session_factory, "EAT_HUMAN", duration=54000)

    async def test_eats_without_ambush(self, send, session_factory, ambush):
        ambush(0)
        await self._seed(session_factory, eat_humans=2)

        (reply,) = await send("Сожрать человека", uid=UID)

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.eat_humans == 3
        restored = ghoul.hunger - 10
        assert reply == (
            f"🍽 Ты сожрал человека. \n\n🍖 Голод восстановлен на {restored}%, "
            f"теперь: {ghoul.hunger}%\n🥩 Всего съедено людей: 3"
        )
        assert await mob_battles(session_factory, UID) == (0, 0, 0)

    async def test_cooldown(self, send, session_factory, ambush):
        ambush(0)
        await self._seed(session_factory)
        await send("сожрать человека", uid=UID)

        (reply,) = await send("сожрать человека", uid=UID)

        # 14 или ровно 15 часов: остаток округляется до секунд
        assert reply.startswith(
            "А не дохуя ли ты у нас жрать собрался? Попробуй через 1"
        )
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.eat_humans == 1

    async def test_sends_gif_when_one_exists(
        self, feed, telegram, session_factory, ambush, assets
    ):
        ambush(0)
        folder = assets / "animation" / "eat"
        folder.mkdir(parents=True)
        (folder / "eat.mp4").write_bytes(b"gif-bytes")
        await self._seed(session_factory)

        telegram = await feed(message_update("сожрать человека", uid=UID))

        (body,) = telegram.bodies("sendAnimation")
        assert body["animation"] == "<file:eat.mp4>"
        assert body["caption"].startswith("🍽 Ты сожрал человека.")

    async def test_ambush_won_then_eats(self, feed, session_factory, ambush, mob):
        ambush(100)
        mob("weak")
        await self._seed(session_factory, **STRONG_PLAYER)

        telegram = await feed(message_update("сожрать человека", uid=UID))

        assert telegram.methods_called("sendRichMessage") == 1
        ambushed, rewards, eaten = telegram.sent
        assert ambushed.startswith("🐺 Пока ты подкрадывался к добыче")
        assert rewards.startswith("📈 Получено опыта: ")
        assert rewards.endswith("\n\n🍽 Соперник повержен - человек твой.")
        assert eaten.startswith("🍽 Ты сожрал человека.")

        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.eat_humans == 1
        assert await mob_battles(session_factory, UID) == (1, 1, 0)
        assert not await is_busy(session_factory, UID)

    async def test_ambush_lost_spends_cooldown(
        self, send, session_factory, ambush, mob
    ):
        ambush(100)
        mob("strong")
        await self._seed(session_factory, **HARMLESS_PLAYER)

        ambushed, lost = await send("сожрать человека", uid=UID)

        assert ambushed.startswith("🐺 ")
        assert lost == "Моб оказался сильнее - человек достался ему."
        ghoul = await get_ghoul(session_factory, UID)
        assert ghoul is not None and ghoul.eat_humans == 0 and ghoul.hunger == 10
        (again,) = await send("сожрать человека", uid=UID)
        assert again.startswith("А не дохуя ли ты у нас жрать собрался?")

    async def test_ambush_draw(self, send, session_factory, ambush, mob):
        ambush(100)
        mob("mirror")
        # голод в засаде не влияет на исход, но меняет эффективные статы игрока:
        # для честного зеркала он полный, как у моба
        await self._seed(session_factory, **HARMLESS_PLAYER, hunger=100)

        ambushed, draw = await send("сожрать человека", uid=UID)

        assert draw == "Ничья - в суматохе добыча сбежала, поесть не вышло."

    async def test_busy_player_is_not_ambushed(
        self, send, session_factory, ambush, mob
    ):
        ambush(100)
        mob("strong")
        await self._seed(session_factory, **STRONG_PLAYER)
        await claim_mob_fight(session_factory, UID)

        (reply,) = await send("сожрать человека", uid=UID)

        assert reply.startswith("🍽 Ты сожрал человека.")
        assert await mob_battles(session_factory, UID) == (0, 0, 0)

    async def test_ambush_ignores_combat_readiness(
        self, send, session_factory, ambush, mob
    ):
        # как у прода: засада нападает и на гуля, которому "бить моба" отказал бы
        ambush(100)
        mob("weak")
        await self._seed(session_factory, **{**STRONG_PLAYER, "health": 1})

        replies = await send("сожрать человека", uid=UID)

        assert replies[0].startswith("🐺 ")
