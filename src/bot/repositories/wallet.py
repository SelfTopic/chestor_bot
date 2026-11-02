from dataclasses import dataclass
from typing import Any

from sqlalchemy import BigInteger, String, desc, exists, func, literal, select, union_all, update
from sqlalchemy.dialects.postgresql import aggregate_order_by, array
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ...database.models import Family, FamilyMember, User
from .base import Base
from .chat_participant import in_chat


@dataclass(frozen=True)
class TopWallet:
    balance: int
    names: list[str]
    member_ids: list[int]
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

    async def top(self, limit: int, chat_id: int | None = None) -> list[TopWallet]:
        wallets, order = self._ranking(chat_id)
        rows = await self.session.execute(
            select(
                wallets.c.balance,
                wallets.c.names,
                wallets.c.member_ids,
                wallets.c.family_name,
                wallets.c.is_family,
            )
            .order_by(*order)
            .limit(limit)
        )
        return [
            TopWallet(balance, list(names), list(member_ids), family_name, is_family)
            for balance, names, member_ids, family_name, is_family in rows
        ]

    async def place(self, telegram_id: int, chat_id: int | None = None) -> int | None:
        wallets, order = self._ranking(chat_id)
        ranked = select(
            wallets.c.telegram_id,
            wallets.c.family_id,
            func.row_number().over(order_by=order).label("place"),
        ).subquery()
        family_id = await self._family_id(telegram_id)
        mine = (
            ranked.c.telegram_id == telegram_id
            if family_id is None
            else ranked.c.family_id == family_id
        )
        return await self.session.scalar(select(ranked.c.place).where(mine))

    # Семья попадает в топ чата, если в чате есть хоть один её член. Место в топе считается
    # тем же порядком, что и список: у равных балансов последний ключ — владелец.
    def _ranking(self, chat_id: int | None) -> tuple[Any, list[Any]]:
        member = exists().where(FamilyMember.telegram_id == User.telegram_id)
        singles = select(
            User.balance.label("balance"),
            array([User.first_name]).label("names"),
            array([User.telegram_id]).label("member_ids"),
            literal(None, String).label("family_name"),
            literal(False).label("is_family"),
            User.telegram_id.label("telegram_id"),
            literal(None, BigInteger).label("family_id"),
        ).where(~member)
        if chat_id is not None:
            singles = singles.where(in_chat(chat_id, User.telegram_id))
        families = (
            select(
                Family.balance.label("balance"),
                func.array_agg(aggregate_order_by(User.first_name, FamilyMember.joined_at)).label(
                    "names"
                ),
                func.array_agg(
                    aggregate_order_by(User.telegram_id, FamilyMember.joined_at)
                ).label("member_ids"),
                Family.name.label("family_name"),
                literal(True).label("is_family"),
                literal(None, BigInteger).label("telegram_id"),
                Family.id.label("family_id"),
            )
            .join(FamilyMember, FamilyMember.family_id == Family.id)
            .join(User, User.telegram_id == FamilyMember.telegram_id)
            .group_by(Family.id)
        )
        if chat_id is not None:
            present = aliased(FamilyMember)
            families = families.where(
                Family.id.in_(
                    select(present.family_id).where(in_chat(chat_id, present.telegram_id))
                )
            )
        wallets = union_all(singles, families).subquery()
        order = [
            desc(wallets.c.balance),
            wallets.c.is_family,
            wallets.c.telegram_id,
            wallets.c.family_id,
        ]
        return wallets, order
