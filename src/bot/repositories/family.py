from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import (
    Family,
    FamilyMember,
    MarriageConsent,
    MarriageProposal,
    User,
)
from .base import Base


@dataclass(frozen=True)
class Member:
    telegram_id: int
    joined_at: datetime


class FamilyRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # Все изменения состава семей сначала берут эту блокировку: двое не вступят в брак с
    # одним человеком одновременно и развод не разминётся со свадьбой. Порядок id —
    # чтобы две транзакции не ждали друг друга по кругу.
    async def lock_users(self, telegram_ids: set[int]) -> None:
        await self.session.execute(
            select(User.telegram_id)
            .where(User.telegram_id.in_(telegram_ids))
            .order_by(User.telegram_id)
            .with_for_update()
        )

    async def family_id_of(self, telegram_id: int) -> int | None:
        return await self.session.scalar(
            select(FamilyMember.family_id).where(FamilyMember.telegram_id == telegram_id)
        )

    async def same_family(self, first_id: int, second_id: int) -> bool:
        first = await self.family_id_of(first_id)
        return first is not None and first == await self.family_id_of(second_id)

    async def family(self, family_id: int) -> Family | None:
        return await self.session.get(Family, family_id)

    async def members(self, family_id: int) -> list[Member]:
        rows = await self.session.execute(
            select(FamilyMember.telegram_id, FamilyMember.joined_at)
            .where(FamilyMember.family_id == family_id)
            .order_by(FamilyMember.joined_at, FamilyMember.telegram_id)
        )
        return [Member(telegram_id, joined_at) for telegram_id, joined_at in rows]

    async def create_family(self) -> Family:
        family = Family(balance=0)
        self.session.add(family)
        await self.session.flush()
        return family

    async def add_member(self, family_id: int, telegram_id: int) -> None:
        await self.session.execute(
            insert(FamilyMember).values(family_id=family_id, telegram_id=telegram_id)
        )

    async def remove_member(self, telegram_id: int) -> None:
        await self.session.execute(
            delete(FamilyMember).where(FamilyMember.telegram_id == telegram_id)
        )

    async def change_balance(self, family_id: int, delta: int) -> int:
        balance = await self.session.scalar(
            update(Family)
            .where(Family.id == family_id)
            .values(balance=Family.balance + delta)
            .returning(Family.balance)
        )
        assert balance is not None
        return balance

    async def dissolve(self, family_id: int) -> int:
        balance = await self.session.scalar(
            select(Family.balance).where(Family.id == family_id).with_for_update()
        )
        assert balance is not None
        await self.session.execute(
            update(Family)
            .where(Family.id == family_id)
            .values(balance=0, dissolved_at=func.now())
        )
        return balance

    async def create_proposal(
        self, proposer_id: int, target_id: int, family_id: int | None, chat_id: int
    ) -> MarriageProposal:
        proposal = MarriageProposal(
            proposer_telegram_id=proposer_id,
            target_telegram_id=target_id,
            family_id=family_id,
            chat_id=chat_id,
            stage="awaiting",
        )
        self.session.add(proposal)
        await self.session.flush()
        return proposal

    async def has_awaiting(self, proposer_id: int, target_id: int) -> bool:
        found = await self.session.scalar(
            select(MarriageProposal.id).where(
                MarriageProposal.proposer_telegram_id == proposer_id,
                MarriageProposal.target_telegram_id == target_id,
                MarriageProposal.stage == "awaiting",
            )
        )
        return found is not None

    # Блокировка строки предложения выстраивает нажатия в очередь: иначе два последних
    # согласия в соседних транзакциях не увидели бы друг друга и брак не заключился бы.
    async def lock_proposal(self, proposal_id: int) -> MarriageProposal | None:
        return await self.session.scalar(
            select(MarriageProposal)
            .where(MarriageProposal.id == proposal_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

    async def proposal(self, proposal_id: int) -> MarriageProposal | None:
        return await self.session.get(MarriageProposal, proposal_id)

    async def set_message(self, proposal_id: int, message_id: int) -> None:
        await self.session.execute(
            update(MarriageProposal)
            .where(MarriageProposal.id == proposal_id)
            .values(message_id=message_id)
        )

    async def finish(
        self, proposal_id: int, stage: str, declined_by: int | None = None
    ) -> MarriageProposal | None:
        return await self.session.scalar(
            update(MarriageProposal)
            .where(MarriageProposal.id == proposal_id, MarriageProposal.stage == "awaiting")
            .values(stage=stage, declined_by=declined_by)
            .returning(MarriageProposal)
            .execution_options(populate_existing=True)
        )

    async def consents(self, proposal_id: int) -> set[int]:
        rows = await self.session.scalars(
            select(MarriageConsent.telegram_id).where(
                MarriageConsent.proposal_id == proposal_id
            )
        )
        return set(rows)

    async def add_consent(self, proposal_id: int, telegram_id: int) -> None:
        await self.session.execute(
            insert(MarriageConsent)
            .values(proposal_id=proposal_id, telegram_id=telegram_id)
            .on_conflict_do_nothing()
        )

    async def overdue(self, lifetime: timedelta) -> list[int]:
        rows = await self.session.scalars(
            select(MarriageProposal.id).where(
                MarriageProposal.stage == "awaiting",
                MarriageProposal.created_at < func.now() - lifetime,
            )
        )
        return list(rows)
