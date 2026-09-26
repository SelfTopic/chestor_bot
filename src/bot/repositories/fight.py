from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.repositories import GhoulRepository
from src.database.models import Battle, Ghoul, User


@dataclass(frozen=True)
class Score:
    wins: int
    losses: int
    total: int


@dataclass(frozen=True)
class RecentBattles:
    pair: int
    initiator: int
    target: int


class FightRepository:
    def __init__(self, session: AsyncSession, ghoul_repository: GhoulRepository) -> None:
        self.session = session
        self._ghouls = ghoul_repository

    async def participants(self, *telegram_ids: int) -> dict[int, tuple[User, Ghoul | None]]:
        rows = await self.session.execute(
            select(User, Ghoul)
            .outerjoin(Ghoul, Ghoul.telegram_id == User.telegram_id)
            .where(User.telegram_id.in_(telegram_ids))
        )
        found: dict[int, tuple[User, Ghoul | None]] = {}
        for user, ghoul in rows.tuples():
            if ghoul is not None:
                ghoul.kagune_type_bit = self._ghouls._validate_kagune_bit(
                    ghoul.kagune_type_bit
                )
            found[user.telegram_id] = (user, ghoul)
        return found

    async def scores(self, telegram_ids: Sequence[int], battle_type: str) -> dict[int, Score]:
        a = Battle.participant_a_telegram_id
        b = Battle.participant_b_telegram_id
        winner = Battle.winner

        columns = []
        for telegram_id in telegram_ids:
            won = or_(and_(a == telegram_id, winner == "a"), and_(b == telegram_id, winner == "b"))
            lost = or_(and_(a == telegram_id, winner == "b"), and_(b == telegram_id, winner == "a"))
            took_part = or_(a == telegram_id, b == telegram_id)
            columns += [
                func.count().filter(won),
                func.count().filter(lost),
                func.count().filter(took_part),
            ]

        row = (
            await self.session.execute(
                select(*columns).where(
                    Battle.battle_type == battle_type,
                    or_(a.in_(telegram_ids), b.in_(telegram_ids)),
                )
            )
        ).one()
        return {
            telegram_id: Score(*row[i * 3 : i * 3 + 3])
            for i, telegram_id in enumerate(telegram_ids)
        }

    async def recent_battles(self, initiator: int, target: int, since: datetime) -> RecentBattles:
        a = Battle.participant_a_telegram_id
        b = Battle.participant_b_telegram_id
        pair = or_(and_(a == initiator, b == target), and_(a == target, b == initiator))
        row = (
            await self.session.execute(
                select(
                    func.count().filter(pair),
                    func.count().filter(or_(a == initiator, b == initiator)),
                    func.count().filter(or_(a == target, b == target)),
                ).where(
                    Battle.created_at >= since,
                    or_(a.in_([initiator, target]), b.in_([initiator, target])),
                )
            )
        ).one()
        return RecentBattles(*row)
