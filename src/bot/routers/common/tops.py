import logging

from aiogram import Router
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...filters import Text
from ...services import UserService

logger = logging.getLogger(__name__)

router = Router(name=__name__)


@router.message(Text("топ бал", startswith=True))
@inject
async def top_balance_handler(
    message: Message,
    user_service: UserService = Provide[Container.user_service],
) -> None:
    if not message.text:
        raise

    count = 20

    if message.text.lower() != "топ бал":
        count = message.text.split()[2]

    if isinstance(count, str) and not count.isdigit():
        await message.reply("Топ нужно указывать положительной цифрой в диапазоне 1-50")
        return

    count = int(count)

    if count < 1 or count > 50:
        await message.reply("Топ нужно указывать положительной цифрой в диапазоне 1-50")
        return

    top = await user_service.get_top_balance(count)

    start_message = f"Топ {count} самых богатих гулий: \n\n"
    for i, user in enumerate(top, start=1):
        start_message += f"{i}. {user.first_name} - {user.balance} CheSton\n"

    await message.answer(text=start_message)
