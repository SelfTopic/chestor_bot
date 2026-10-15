from dataclasses import dataclass

from sqlalchemy import String, desc, exists, func, literal, select, union_all, update
from sqlalchemy.dialects.postgresql import aggregate_order_by, array
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import Family, FamilyMember, User
from .base import Base


@dataclass(frozen=True)
class TopWallet:
    balance: int
    names: list[str]
    family_name: str | None
    is_family: bool


# Кошелёк игрока: у члена семьи — счёт семьи, личного баланса у него нет; у свободного —
# свой баланс.
class WalletRepository(Base):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _family_id(self, telegram_id: int) -> int | None:
        return await self.session.scalar(
            select(FamilyMember.family_id).where(FamilyMember.telegram_id == telegram_id)
        )

    async def balance(self, telegram_id: int) -> int | None:
        return await self.session.scalar(
            select(func.coalesce(Family.balance, User.balance))
            .select_from(User)
            .outerjoin(FamilyMember, FamilyMember.telegram_id == User.telegram_id)
            .outerjoin(Family, Family.id == FamilyMember.family_id)
            .where(User.telegram_id == telegram_id)
        )

    async def change(self, telegram_id: int, delta: int) -> int | None:
        return await self._update(telegram_id, delta, at_least=None)

    # Проверка баланса в WHERE того же UPDATE: между проверкой и списанием нет гонки.
    async def debit_if_sufficient(self, telegram_id: int, amount: int) -> int | None:
        return await self._update(telegram_id, -amount, at_least=amount)

    async def _update(self, telegram_id: int, delta: int, at_least: int | None) -> int | None:
        family_id = await self._family_id(telegram_id)
        if family_id is None:
            stmt = update(User).where(User.telegram_id == telegram_id)
            if at_least is not None:
                stmt = stmt.where(User.balance >= at_least)
            return await self.session.scalar(
                stmt.values(balance=User.balance + delta).returning(User.balance)
            )

        stmt = update(Family).where(Family.id == family_id)
        if at_least is not None:
            stmt = stmt.where(Family.balance >= at_least)
        return await self.session.scalar(
            stmt.values(balance=Family.balance + delta).returning(Family.balance)
        )

    async def top(self, limit: int) -> list[TopWallet]:
        member = exists().where(FamilyMember.telegram_id == User.telegram_id)
        singles = select(
            User.balance.label("balance"),
            array([User.first_name]).label("names"),
            literal(None, String).label("family_name"),
            literal(False).label("is_family"),
        ).where(~member)
        families = (
            select(
                Family.balance.label("balance"),
                func.array_agg(aggregate_order_by(User.first_name, FamilyMember.joined_at)).label(
                    "names"
                ),
                Family.name.label("family_name"),
                literal(True).label("is_family"),
            )
            .join(FamilyMember, FamilyMember.family_id == Family.id)
            .join(User, User.telegram_id == FamilyMember.telegram_id)
            .group_by(Family.id)
        )
        wallets = union_all(singles, families).subquery()
        rows = await self.session.execute(
            select(wallets).order_by(desc(wallets.c.balance)).limit(limit)
        )
        return [
            TopWallet(balance, list(names), family_name, is_family)
            for balance, names, family_name, is_family in rows
        ]
