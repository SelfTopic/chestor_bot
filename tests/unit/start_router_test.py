import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Chat, Message, User

from src.bot.routers.common.start_router import start_handler


@pytest.mark.asyncio
async def test_start_router():
    mock_user_service = AsyncMock()
    mock_user_service.get.return_value = MagicMock(
        id=1, first_name="Alex", telegram_id=123
    )

    mock_dialog_service = MagicMock()
    mock_dialog_service.text.return_value = "Hello, Alex"

    fake_user = User(id=123, is_bot=False, first_name="Alex")
    fake_chat = Chat(
        id=1,
        type="private",
    )
    fake_message = Message(
        message_id=1,
        date=datetime.datetime.now(),
        chat=fake_chat,
        from_user=fake_user,
        text="/start",
    )

    result = await start_handler(
        message=fake_message,
        user_service=mock_user_service,
        dialog_service=mock_dialog_service,
    )

    mock_user_service.get.assert_awaited_once_with(1)
    mock_dialog_service.text.assert_called_once_with(key="start", name="John")
