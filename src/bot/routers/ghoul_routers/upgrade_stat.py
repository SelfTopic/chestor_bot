import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from dependency_injector.wiring import Provide, inject

from ...containers import Container
from ...exceptions import GhoulNotFoundInDatabase
from ...services.stat_upgrade import StatUpgradeService

router = Router(name=__name__)

logger = logging.getLogger(__name__)


@router.message(F.text.lower() == "качаться")
@inject
async def upgrade_stat_handler(
    message: Message,
    stat_service: StatUpgradeService = Provide[Container.stat_upgrade_service],
):
    if not message.from_user:
        raise ValueError("User from message not found")

    if message.chat.type != "private":
        await message.reply(
            text="Эта команда работает только в личных сообщениях с ботом."
        )
        return

    ghoul = await stat_service.ghoul_service.get(message)

    if not ghoul:
        raise GhoulNotFoundInDatabase("Ghoul not found for user")

    user = await stat_service.user_service.get(find_by=message.from_user.id)
    text, keyboard = stat_service.build_message(ghoul, user)
    await message.reply(text=text, reply_markup=keyboard)


@router.callback_query(
    lambda c: c.data and (c.data.startswith("stat_buy_") or c.data == "stat_nop")
)
@inject
async def stat_upgrade_callback(
    callback_query: CallbackQuery,
    stat_service: StatUpgradeService = Provide[Container.stat_upgrade_service],
):
    if not callback_query.data:
        raise ValueError("Callback data is missing")

    if not isinstance(callback_query.message, Message):
        await callback_query.answer("Невозможно обработать запрос")
        return

    if callback_query.message.chat.type != "private":
        await callback_query.answer("Эта операция доступна только в личных сообщениях.")
        return

    data = callback_query.data
    if data == "stat_nop":
        await callback_query.answer("Достигнут предел прокачки для этого стата.")
        return

    payload = data[len("stat_buy_") :]
    try:
        stat_key, count_str = payload.rsplit("_", 1)
    except ValueError:
        await callback_query.answer("Неверные данные кнопки")
        return

    try:
        count = int(count_str)
    except ValueError:
        await callback_query.answer("Неверное количество")
        return

    allowed = {
        "strength": "💪Сила",
        "dexterity": "🤸‍♂️Ловкость",
        "speed": "🏃Скорость",
        "max_health": "❤️Макс. здоровье",
        "regeneration": "❣️Регенерация",
    }

    if stat_key not in allowed:
        await callback_query.answer("Неверный стат")
        return

    new_ghoul, new_user, bought, price = await stat_service.purchase(
        telegram_id=callback_query.from_user.id, stat_key=stat_key, count=count
    )

    if bought == 0 and price > 0:
        await callback_query.answer("Недостаточно средств")
        return

    if bought == 0 and price == 0:
        await callback_query.answer("Достигнут предел прокачки для этого стата.")
        return

    new_text, new_kb = stat_service.build_message(new_ghoul, new_user)

    await callback_query.message.edit_text(text=new_text, reply_markup=new_kb)
    await callback_query.answer(
        f"Прокачано {allowed[stat_key]} +{bought}. Потрачено: {price}"
    )
