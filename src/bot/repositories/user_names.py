from collections.abc import Collection

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ChatNickname, User


class UserNameRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def names(
        self, telegram_ids: Collection[int], chat_id: int | None = None
    ) -> dict[int, str]:
        if not telegram_ids:
            return {}
        name = func.coalesce(ChatNickname.nickname, User.first_name)
        rows = await self.session.execute(
            select(User.telegram_id, name)
            .outerjoin(
                ChatNickname,
                and_(
                    ChatNickname.telegram_id == User.telegram_id,
                    ChatNickname.chat_id == chat_id,
                ),
            )
            .where(User.telegram_id.in_(telegram_ids))
        )
        return {telegram_id: name for telegram_id, name in rows.tuples()}

    async def usernames(self, telegram_ids: Collection[int]) -> dict[int, str]:
        rows = await self.session.execute(
            select(User.telegram_id, User.username).where(
                User.telegram_id.in_(telegram_ids), User.username.is_not(None)
            )
        )
        return {telegram_id: username for telegram_id, username in rows.tuples() if username}

    async def nicknames(self, telegram_ids: Collection[int], chat_id: int) -> dict[int, str]:
        rows = await self.session.execute(
            select(ChatNickname.telegram_id, ChatNickname.nickname).where(
                ChatNickname.chat_id == chat_id, ChatNickname.telegram_id.in_(telegram_ids)
            )
        )
        return {telegram_id: nickname for telegram_id, nickname in rows.tuples()}
