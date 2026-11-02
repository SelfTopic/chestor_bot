from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import ChatNickname


class NicknameRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def in_chat(self, chat_id: int) -> dict[int, str]:
        rows = await self.session.execute(
            select(ChatNickname.telegram_id, ChatNickname.nickname).where(
                ChatNickname.chat_id == chat_id
            )
        )
        return {telegram_id: nickname for telegram_id, nickname in rows.tuples()}

    async def set(self, chat_id: int, telegram_id: int, nickname: str) -> None:
        stmt = insert(ChatNickname).values(
            chat_id=chat_id, telegram_id=telegram_id, nickname=nickname
        )
        await self.session.execute(
            stmt.on_conflict_do_update(
                index_elements=["chat_id", "telegram_id"],
                set_={"nickname": nickname, "set_at": stmt.excluded.set_at},
            )
        )

    async def delete(self, chat_id: int, telegram_id: int) -> str | None:
        return await self.session.scalar(
            delete(ChatNickname)
            .where(ChatNickname.chat_id == chat_id, ChatNickname.telegram_id == telegram_id)
            .returning(ChatNickname.nickname)
        )
