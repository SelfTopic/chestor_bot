import logging
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.types.rp_commands import TypeRpCommandEnum
from src.database.models import Rp

from .base import Base

logger = logging.getLogger(__name__)


class RpCommandsRepository(Base):
    session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_chat_id_and_command(
        self,
        chat_id: int,
        command: str,
    ) -> Optional[Rp]:
        logger.debug(f"Getting RP command for chat_id={chat_id} and command={command}")
        stmt = select(Rp).where(Rp.chat_id == chat_id, Rp.command == command)
        result = await self.session.execute(stmt)
        logger.debug(f"RP command result: {result}")
        return result.scalars().first()

    async def insert(
        self,
        chat_id: int,
        command: str,
        action: str,
        type_command: TypeRpCommandEnum,
        file_id: Optional[str] = None,
    ) -> Rp:
        logger.debug(
            f"Inserting/updating RP command for chat_id={chat_id}, command={command}, action={action}, type_command={type_command}, file_id={file_id}"
        )
        stmt = (
            insert(Rp)
            .values(
                chat_id=chat_id,
                command=command,
                action=action,
                type_command=type_command,
                file_id=file_id,
            )
            .on_conflict_do_update(
                index_elements=["chat_id", "command"],
                set_=dict(action=action, type_command=type_command, file_id=file_id),
            )
            .returning(Rp)
        )

        result = await self.session.execute(stmt)
        rp = result.scalar_one()
        logger.debug(f"Inserted/updated RP command: {rp}")
        return rp

    async def delete_by_chat_id_and_command(
        self,
        chat_id: int,
        command: str,
    ) -> None:
        logger.debug(f"Deleting RP command for chat_id={chat_id} and command={command}")
        stmt = delete(Rp).where(Rp.chat_id == chat_id, Rp.command == command)
        await self.session.execute(stmt)
        logger.debug(f"RP command for chat_id={chat_id} and command={command} deleted")

    async def delete_by_chat_id(self, chat_id: int) -> None:
        logger.debug(f"Deleting RP commands for chat_id={chat_id}")
        stmt = delete(Rp).where(Rp.chat_id == chat_id)
        await self.session.execute(stmt)
        logger.debug(f"RP commands for chat_id={chat_id} deleted")

    async def get_by_chat_id(self, chat_id: int) -> list[Rp]:
        logger.debug(f"Getting RP commands for chat_id={chat_id}")
        stmt = select(Rp).where(Rp.chat_id == chat_id)
        result = await self.session.execute(stmt)
        rp_commands = list(result.scalars().all())
        logger.debug(f"RP commands for chat_id={chat_id}: {rp_commands}")
        return rp_commands
