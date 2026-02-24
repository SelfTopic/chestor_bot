import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from src.bot.repositories.chat import ChatRepository
from src.bot.repositories.user import UserRepository

logger = logging.getLogger(__name__)


@dataclass
class BroadcastResult:
    total: int
    success: int
    failed: int


class BroadcastService:
    def __init__(self, user_repo: UserRepository, chat_repo: ChatRepository, bot: Bot):
        self.user_repo = user_repo
        self.chat_repo = chat_repo
        self.bot = bot

    async def send_to_user(self, telegram_id: int, text: str) -> bool:
        try:
            await self.bot.send_message(
                chat_id=telegram_id, text=text, parse_mode="HTML"
            )
            return True
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.warning(f"Cannot send to user {telegram_id}: {e}")
            return False

    async def send_to_chat(self, telegram_id: int, text: str) -> bool:
        try:
            await self.bot.send_message(
                chat_id=telegram_id, text=text, parse_mode="HTML"
            )
            return True
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.warning(f"Cannot send to chat {telegram_id}: {e}")
            return False

    async def broadcast_to_private(self, text: str) -> BroadcastResult:
        """Рассылка всем пользователям у которых есть личка с ботом."""
        users = await self.user_repo.get_all_with_private_chat()
        return await self._broadcast(
            targets=[u.telegram_id for u in users],
            text=text,
            sender=self.send_to_user,
        )

    async def broadcast_to_chats(self, text: str) -> BroadcastResult:
        """Рассылка во все известные группы."""
        chats = await self.chat_repo.get_all()
        return await self._broadcast(
            targets=[c.telegram_id for c in chats],
            text=text,
            sender=self.send_to_chat,
        )

    async def broadcast_to_all(self, text: str) -> BroadcastResult:
        """Рассылка и в личку и в группы."""
        private = await self.broadcast_to_private(text)
        chats = await self.broadcast_to_chats(text)
        return BroadcastResult(
            total=private.total + chats.total,
            success=private.success + chats.success,
            failed=private.failed + chats.failed,
        )

    async def send_to_target(self, query: str, text: str) -> bool:
        """Отправка конкретному получателю — id или @username."""
        if query.lstrip("-").isdigit():
            target_id = int(query)
        else:
            username = query.lstrip("@")
            user = await self.user_repo.get(username)
            if not user:
                raise ValueError(f"Пользователь не найден: {query}")
            target_id = user.telegram_id

        return await self.send_to_user(target_id, text)

    async def _broadcast(
        self, targets: list[int], text: str, sender
    ) -> BroadcastResult:
        success, failed = 0, 0
        for target_id in targets:
            result = await sender(target_id, text)
            if result:
                success += 1
            else:
                failed += 1
            await asyncio.sleep(0.05)  # flood control — 20 msg/s
        return BroadcastResult(total=len(targets), success=success, failed=failed)
