from dataclasses import dataclass

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import RouletteMachine
from .base import Base


@dataclass(frozen=True)
class OpenRoulette:
    machine_id: int
    chat_id: int
    telegram_id: int
    message_id: int | None
    position: int


class RouletteRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def open_machine(self, chat_id: int, telegram_id: int, position: int) -> int | None:
        stmt = (
            insert(RouletteMachine)
            .values(chat_id=chat_id, telegram_id=telegram_id, position=position)
            .on_conflict_do_nothing(
                index_elements=[RouletteMachine.chat_id, RouletteMachine.telegram_id],
                index_where=text("closed_at IS NULL"),
            )
            .returning(RouletteMachine.id)
        )
        return await self.session.scalar(stmt)

    async def set_message(self, machine_id: int, message_id: int) -> None:
        await self.session.execute(
            update(RouletteMachine)
            .where(RouletteMachine.id == machine_id)
            .values(message_id=message_id)
        )

    async def set_position(self, machine_id: int, position: int) -> None:
        await self.session.execute(
            update(RouletteMachine).where(RouletteMachine.id == machine_id).values(position=position)
        )

    async def close_machine(self, machine_id: int) -> None:
        await self.session.execute(
            update(RouletteMachine)
            .where(RouletteMachine.id == machine_id, RouletteMachine.closed_at.is_(None))
            .values(closed_at=func.now())
        )

    async def open_machines(self) -> list[OpenRoulette]:
        rows = await self.session.execute(
            select(
                RouletteMachine.id,
                RouletteMachine.chat_id,
                RouletteMachine.telegram_id,
                RouletteMachine.message_id,
                RouletteMachine.position,
            ).where(RouletteMachine.closed_at.is_(None))
        )
        return [OpenRoulette(*row) for row in rows]
