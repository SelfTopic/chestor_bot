import logging

from aiogram import Router
from aiogram.types import Message
from dependency_injector.wiring import Provide, inject

from src.bot.containers import Container
from src.bot.services import GhoulService, UserService

from ...filters import Text

router = Router(name=__name__)

logger = logging.getLogger(__name__)


@router.message(Text("топ щелк", startswith=True))
@inject
async def top_snap_handler(
    message: Message,
    ghoul_service: GhoulService = Provide[Container.ghoul_service],
    user_service: UserService = Provide[Container.user_service],
) -> None:
    count = 20

    if not message.text:
        raise

    if message.text != "топ щелк":
        count = message.text.split("топ щелк")[1]

        if not count.isdigit():
            await message.answer("Топ нужно указывать цифрой")
            return

        count = int(count)

    if count < 1 or count > 50:
        await message.answer("Топ не может выходить за пределы значений 1-50")
        return

    top = await ghoul_service.get_top_snap(count)

    if not top:
        await message.answer("А нету топа прикинь нахуй.")
        return

    answer_text = f"Топ {count} самых сломанных пальцев\n\n"

    for c, i in enumerate(top, start=1):
        user = await user_service.get(find_by=i.telegram_id)

        answer_text += f"{c}. {user.first_name if user else 'Unknown'} - {i.snap_count}"

    await message.answer(answer_text)
