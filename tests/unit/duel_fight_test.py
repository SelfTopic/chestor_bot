from datetime import timedelta
from typing import cast

from aiogram import Bot

from src.bot.repositories.duel_session import DuelSessionRepository
from src.bot.repositories.ghoul import GhoulRepository
from src.bot.routers.ghoul_routers.duel.fight import finalize_outcome, run_and_announce_fight
from src.bot.routers.ghoul_routers.duel.services import build_services
from src.bot.utils import utcnow_naive


class _FakeMessage:
    def __init__(self, message_id: int) -> None:
        self.message_id = message_id


class _FakeBot:
    """Дублёр Bot без реального похода в Telegram - только то, что реально
    вызывает `run_and_announce_fight`/`LevelUpService`."""

    def __init__(self) -> None:
        self._next_id = 0

    async def send_rich_message(self, chat_id, rich_message, reply_markup=None, **kwargs):
        self._next_id += 1
        return _FakeMessage(self._next_id)

    async def send_message(self, chat_id, text=None, reply_markup=None, **kwargs):
        self._next_id += 1
        return _FakeMessage(self._next_id)

    async def edit_message_text(self, *args, **kwargs):
        return None

    async def edit_message_reply_markup(self, *args, **kwargs):
        return None


async def test_run_and_announce_fight_refreshes_health_updated_at_for_both_sides(
    session, make_user, make_ghoul
):
    """Регрессия по реальному багу с живого теста: после дуэли у победителя
    HP "магически" вернулось на максимум, потому что запись нового health
    не двигала health_updated_at - следующий materialize_passive_stats
    (вызывается GhoulService.get, например при "распрофиль") пересчитывал
    реген от СТАРОЙ метки времени поверх уже честно списанного урона.
    health_updated_at обязан обновиться у ОБЕИХ сторон сразу после боя,
    независимо от того, кто победил."""

    stale_timestamp = utcnow_naive() - timedelta(hours=100)

    await make_user(telegram_id=700_000_001)
    await make_user(telegram_id=700_000_002, username="tw_700002")
    await make_ghoul(
        telegram_id=700_000_001,
        health=5,
        max_health=5,
        regeneration=50,
        health_updated_at=stale_timestamp,
    )
    await make_ghoul(
        telegram_id=700_000_002,
        health=5,
        max_health=5,
        regeneration=50,
        health_updated_at=stale_timestamp,
    )

    duel_session_repository = DuelSessionRepository(session)
    duel_session = await duel_session_repository.create(
        chat_id=-1, initiator_telegram_id=700_000_001, target_telegram_id=700_000_002
    )
    duel_session = await duel_session_repository.atomic_update(
        duel_session.id, "awaiting_consent", stage="running", compress_hp=True
    )
    assert duel_session is not None

    before_fight = utcnow_naive()
    fake_bot = cast(Bot, _FakeBot())
    services = build_services(session, fake_bot)
    await run_and_announce_fight(fake_bot, duel_session, services)

    ghoul_repository = GhoulRepository(session)
    raw_initiator = await ghoul_repository.get(700_000_001)
    raw_target = await ghoul_repository.get(700_000_002)

    assert raw_initiator is not None and raw_target is not None
    assert raw_initiator.health_updated_at >= before_fight
    assert raw_target.health_updated_at >= before_fight


async def test_finalize_outcome_eat_increments_winner_eat_ghouls(session, make_user, make_ghoul):
    """Регрессия: выбор "съесть" убивал проигравшего (apply_death) и мог
    начислить RC, но НИКОГДА не трогал Ghoul.eat_ghouls у победителя -
    распрофиль показывал 0 съеденных гулей, даже если съедения реально
    были. apply_death трогает только строку проигравшего (is_dead +
    death_log), счётчик победителя - отдельная забота вызывающего кода."""

    await make_user(telegram_id=700_000_003)
    await make_user(telegram_id=700_000_004, username="tw_700004")
    await make_ghoul(telegram_id=700_000_003, health=50, max_health=50, eat_ghouls=2)
    await make_ghoul(telegram_id=700_000_004, health=50, max_health=50, eat_ghouls=0)

    duel_session_repository = DuelSessionRepository(session)
    duel_session = await duel_session_repository.create(
        chat_id=-1, initiator_telegram_id=700_000_003, target_telegram_id=700_000_004
    )
    duel_session = await duel_session_repository.atomic_update(
        duel_session.id,
        "awaiting_consent",
        stage="awaiting_winner_choice",
        winner_telegram_id=700_000_003,
        loser_telegram_id=700_000_004,
    )
    assert duel_session is not None

    fake_bot = cast(Bot, _FakeBot())
    services = build_services(session, fake_bot)
    await finalize_outcome(fake_bot, duel_session, "outcome_eat", services)

    ghoul_repository = GhoulRepository(session)
    winner = await ghoul_repository.get(700_000_003)
    loser = await ghoul_repository.get(700_000_004)

    assert winner is not None and winner.eat_ghouls == 3
    assert loser is not None and loser.is_dead is True
