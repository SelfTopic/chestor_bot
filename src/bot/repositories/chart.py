from dataclasses import dataclass

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import ChartBet, ChartCrashVideo, ChartMachine, ChartRound
from .base import Base


@dataclass(frozen=True)
class AbandonedMachine:
    machine_id: int
    chat_id: int
    message_id: int | None


@dataclass(frozen=True)
class Refund:
    telegram_id: int
    amount: int


@dataclass(frozen=True)
class SettledBet:
    telegram_id: int
    cashed_at: int | None
    payout: int


class ChartRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def open_machine(self, chat_id: int, opened_by: int) -> int | None:
        stmt = (
            insert(ChartMachine)
            .values(chat_id=chat_id, opened_by=opened_by)
            .on_conflict_do_nothing(
                index_elements=[ChartMachine.chat_id], index_where=text("closed_at IS NULL")
            )
            .returning(ChartMachine.id)
        )
        return await self.session.scalar(stmt)

    async def set_message(self, machine_id: int, message_id: int) -> None:
        await self.session.execute(
            update(ChartMachine).where(ChartMachine.id == machine_id).values(message_id=message_id)
        )

    async def close_machine(self, machine_id: int) -> None:
        await self.session.execute(
            update(ChartMachine)
            .where(ChartMachine.id == machine_id, ChartMachine.closed_at.is_(None))
            .values(closed_at=func.now())
        )

    async def start_round(self, machine_id: int, crash: int) -> int:
        stmt = insert(ChartRound).values(machine_id=machine_id, crash=crash).returning(ChartRound.id)
        return (await self.session.execute(stmt)).scalar_one()

    async def add_bet(self, round_id: int, telegram_id: int, amount: int, target: int | None) -> None:
        await self.session.execute(
            insert(ChartBet).values(
                round_id=round_id, telegram_id=telegram_id, amount=amount, target=target, payout=0
            )
        )

    async def cash_out(self, round_id: int, telegram_id: int, cashed_at: int, payout: int) -> None:
        await self.session.execute(
            update(ChartBet)
            .where(ChartBet.round_id == round_id, ChartBet.telegram_id == telegram_id)
            .values(cashed_at=cashed_at, payout=payout)
        )

    async def settle_round(self, round_id: int, bets: list[SettledBet]) -> None:
        for bet in bets:
            await self.session.execute(
                update(ChartBet)
                .where(ChartBet.round_id == round_id, ChartBet.telegram_id == bet.telegram_id)
                .values(cashed_at=bet.cashed_at, payout=bet.payout)
            )
        await self.session.execute(
            update(ChartRound).where(ChartRound.id == round_id).values(settled_at=func.now())
        )

    async def abandoned_machines(self) -> list[AbandonedMachine]:
        rows = await self.session.execute(
            select(ChartMachine.id, ChartMachine.chat_id, ChartMachine.message_id).where(
                ChartMachine.closed_at.is_(None)
            )
        )
        return [AbandonedMachine(*row) for row in rows]

    # Забравшим руками выплата уже ушла; остальным незавершённого раунда — ставка назад.
    async def refunds(self, machine_id: int) -> list[Refund]:
        rows = await self.session.execute(
            select(ChartBet.telegram_id, ChartBet.amount)
            .join(ChartRound, ChartRound.id == ChartBet.round_id)
            .where(
                ChartRound.machine_id == machine_id,
                ChartRound.settled_at.is_(None),
                ChartBet.cashed_at.is_(None),
            )
        )
        return [Refund(*row) for row in rows]

    async def abandon_rounds(self, machine_id: int) -> None:
        await self.session.execute(
            update(ChartRound)
            .where(ChartRound.machine_id == machine_id, ChartRound.settled_at.is_(None))
            .values(settled_at=func.now())
        )

    async def crash_video(self, multiplier: int) -> str | None:
        return await self.session.scalar(
            select(ChartCrashVideo.file_id).where(ChartCrashVideo.multiplier == multiplier)
        )

    async def save_crash_video(self, multiplier: int, file_id: str) -> None:
        stmt = insert(ChartCrashVideo).values(multiplier=multiplier, file_id=file_id)
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=[ChartCrashVideo.multiplier], set_={"file_id": file_id}
            )
        )

    async def forget_crash_video(self, multiplier: int) -> None:
        await self.session.execute(
            delete(ChartCrashVideo).where(ChartCrashVideo.multiplier == multiplier)
        )
