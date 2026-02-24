import logging
from datetime import datetime
from typing import Any, Optional, Union

from sqlalchemy import desc, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import User
from .base import Base

logger = logging.getLogger(__name__)


class UserRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        logger.debug("UserRepository initialized with database session")
        self.session = session

    async def upsert(
        self,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        has_private_chat: Optional[bool] = None,
    ) -> User:
        logger.debug(
            f"Called method upsert. Params: telegram_id={telegram_id}, first_name={first_name}, last_name={last_name}, username={username}"
        )

        upsert_stmt = (
            insert(User)
            .values(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                has_private_chat=has_private_chat
                if has_private_chat is not None
                else False,
            )
            .on_conflict_do_update(
                index_elements=["telegram_id"],
                set_={
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "has_private_chat": has_private_chat
                    if has_private_chat is not None
                    else User.has_private_chat,
                },
            )
            .returning(User)
        )

        user = await self.session.scalar(upsert_stmt)

        if user is None:
            logger.error(f"User ({telegram_id}) not found after UPSERT operation")
            raise Exception(f"User ({telegram_id}) not found after UPSERT operation")

        await self.session.refresh(user)
        logger.debug(f"User record upserted successfully: ID {user.id}")
        return user

    async def get(self, search_parameter: Union[str, int]) -> Optional[User]:
        logger.debug(f"Called method get. Search parameter: {search_parameter}")

        if isinstance(search_parameter, int):
            search_column = User.telegram_id
            search_type = "Telegram ID"
        else:
            search_column = User.username
            search_type = "username"

        user = await self.session.scalar(
            select(User).where(search_column == search_parameter)
        )

        if not user:
            logger.debug(f"User not found by {search_type}: {search_parameter}")
            return None

        logger.debug(f"User found: ID {user.id}")
        return user

    async def get_top_balance(self, limit: int):
        stmt = select(User).order_by(desc(User.balance)).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result)

    async def exists(self, telegram_id: int) -> bool:
        logger.debug(f"Called method exists. Params: telegram_id={telegram_id}")

        exists_query = await self.session.scalar(
            select(exists().where(User.telegram_id == telegram_id))
        )

        if not exists_query:
            logger.error("Exists query returned None (anomaly)")
            raise ValueError("Exists query is not found (anomaly)")

        logger.debug(f"User existence check result: {bool(exists_query)}")
        return bool(exists_query)

    async def change_data(self, telegram_id: int, **kw: Any) -> User:
        logger.debug(
            f"Called method change_data. Params: telegram_id={telegram_id}. Kwargs={kw}"
        )

        exists = await self.exists(telegram_id=telegram_id)

        if not exists:
            logger.error("Cannot change data to nouser")
            raise ValueError("Cannot change data to nouser")

        stmt = (
            insert(User)
            .values(telegram_id=telegram_id, first_name="Mock data")
            .on_conflict_do_update(index_elements=["telegram_id"], set_=kw)
            .returning(User)
        )

        user = await self.session.scalar(stmt)
        await self.session.refresh(user)

        if not user:
            logger.error("Cannot change data to nouser")
            raise ValueError("Cannot change data to nouser")

        return user

    async def ban(
        self,
        telegram_id: int,
        reason: Optional[str] = None,
        banned_until: Optional[datetime] = None,
    ) -> User:
        logger.debug(
            f"Banning user {telegram_id}. Reason: {reason}, Until: {banned_until}"
        )
        return await self.change_data(
            telegram_id,
            is_banned=True,
            ban_reason=reason,
            banned_until=banned_until,
        )

    async def unban(self, telegram_id: int) -> User:
        logger.debug(f"Unbanning user {telegram_id}")
        return await self.change_data(
            telegram_id,
            is_banned=False,
            ban_reason=None,
            banned_until=None,
        )

    async def get_ban_info(self, telegram_id: int) -> Optional[User]:
        """Возвращает пользователя только если он забанен, иначе None"""
        user = await self.get(telegram_id)
        if user and user.is_banned:
            return user
        return None

    async def get_all(self) -> list[User]:
        result = await self.session.scalars(select(User))
        return list(result)

    async def delete(self, telegram_id: int) -> bool:
        user = await self.get(telegram_id)
        if not user:
            return False
        await self.session.delete(user)
        return True

    async def get_all_with_private_chat(self) -> list[User]:
        result = await self.session.scalars(
            select(User).where(User.has_private_chat == True)
        )
        return list(result)


__all__ = ["UserRepository"]
