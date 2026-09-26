"""Репозитории порта: то, что прод читает несколькими запросами, — одним, с теми же числами."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.repositories import ActiveBattleRepository, BattleRepository, GhoulRepository
from src.bot.services import BattleRecordService
from src.bot.utils import utcnow_naive
from src.selfrot_bot.repositories.battle import FightRepository, RecentBattles, Score
from src.selfrot_bot.repositories.users import UserNameRepository

from .test_common_routers import seed
from .test_ghoul_routers import seed_ghoul

A, B, C = 700001, 700002, 700003


@contextmanager
def count_queries(session: AsyncSession) -> Iterator[list[str]]:
    bind = session.bind
    assert bind is not None
    engine = bind.sync_engine
    statements: list[str] = []

    def on_execute(conn, cursor, statement, *args) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", on_execute)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", on_execute)


async def seed_battles(session_factory) -> None:
    for telegram_id in (A, B, C):
        await seed(session_factory, telegram_id)
    async with session_factory() as session:
        repo = BattleRepository(session)
        # (a, b, winner): игрок бывает и на месте "a", и на месте "b"
        for a, b, winner in [(A, B, "a"), (A, B, "b"), (B, A, "a"), (A, C, None), (C, A, "a")]:
            await repo.insert("duel", a, b, None, winner, ended_naturally=True)
        await repo.insert("mob", A, None, "Моб", "a", ended_naturally=True)
        await session.commit()


async def test_duel_scores_match_prod_counters_in_one_query(session_factory):
    await seed_battles(session_factory)

    async with session_factory() as session:
        fights = FightRepository(session, GhoulRepository(session))
        with count_queries(session) as statements:
            scores = await fights.scores([A, B], "duel")

        assert len(statements) == 1
        # A: победа, 3 поражения, ничья с C; B: 2 победы и поражение
        assert scores == {A: Score(1, 3, 5), B: Score(2, 1, 3)}

        records = BattleRecordService(ActiveBattleRepository(session), BattleRepository(session))
        for telegram_id in (A, B):
            assert scores[telegram_id] == Score(
                await records.count_wins_vs_players(telegram_id),
                await records.count_losses_vs_players(telegram_id),
                await records.count_total_battles_vs_players(telegram_id),
            )


async def test_mob_scores_do_not_mix_with_duels(session_factory):
    await seed_battles(session_factory)

    async with session_factory() as session:
        fights = FightRepository(session, GhoulRepository(session))
        assert await fights.scores([A], "mob") == {A: Score(1, 0, 1)}
        assert await fights.scores([B], "mob") == {B: Score(0, 0, 0)}


async def test_participants_in_one_query(session_factory):
    await seed(session_factory, A, "Вася")
    await seed_ghoul(session_factory, A)
    await seed(session_factory, B, "Петя")  # без гуля

    async with session_factory() as session:
        fights = FightRepository(session, GhoulRepository(session))
        with count_queries(session) as statements:
            found = await fights.participants(A, B, C)

    assert len(statements) == 1
    assert set(found) == {A, B}  # C нет в users
    user, ghoul = found[A]
    assert user.first_name == "Вася"
    assert ghoul is not None and ghoul.telegram_id == A
    assert found[B][1] is None


async def test_recent_battles_match_prod_counters_in_one_query(session_factory):
    await seed_battles(session_factory)
    since = utcnow_naive() - timedelta(days=1)

    async with session_factory() as session:
        fights = FightRepository(session, GhoulRepository(session))
        with count_queries(session) as statements:
            recent = await fights.recent_battles(A, B, since)

        assert len(statements) == 1
        # пара A-B: 3 дуэли в обе стороны; у A ещё 2 дуэли с C и моб
        assert recent == RecentBattles(pair=3, initiator=6, target=3)

        records = BattleRecordService(ActiveBattleRepository(session), BattleRepository(session))
        assert recent == RecentBattles(
            await records.count_pair_last_24h(A, B),
            await records.count_total_last_24h(A),
            await records.count_total_last_24h(B),
        )


async def test_recent_battles_ignore_older_ones(session_factory):
    await seed_battles(session_factory)

    async with session_factory() as session:
        fights = FightRepository(session, GhoulRepository(session))
        future = utcnow_naive() + timedelta(minutes=1)
        assert await fights.recent_battles(A, B, future) == RecentBattles(0, 0, 0)


async def test_first_names_in_one_query(session_factory):
    await seed(session_factory, A, "Вася")
    await seed(session_factory, B, "Петя")

    async with session_factory() as session:
        names = UserNameRepository(session)
        with count_queries(session) as statements:
            found = await names.first_names([A, B, C])
            empty = await names.first_names([])

    assert len(statements) == 1  # пустой список в БД не ходит
    assert found == {A: "Вася", B: "Петя"}  # C нет в users
    assert empty == {}
