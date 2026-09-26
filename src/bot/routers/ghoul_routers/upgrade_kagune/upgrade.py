"""Проверки + сама прокачка кагуне, порт прод-хендлера upgrade_kagune.py::_do_upgrade
(там это чистая функция без aiogram — перенесена почти дословно). Переиспользуется и
прямым путём (один тип кагуне) и колбэк-путём (несколько типов) — кулдаун и баланс
перепроверяются здесь заново, а не только один раз при показе клавиатуры, потому что
между показом и нажатием могло пройти время."""

import time
from typing import Any

from selfrot import InlineKeyboard
from selfrot.types import InlineKeyboardMarkup

from src.bot.types import KaguneType
from src.bot.utils import parse_seconds
from src.database.models import Ghoul

from ....context import AppContext
from .callback_data import KaguneUpgradePress


async def do_upgrade(
    ctx: AppContext[Any], telegram_id: int, first_name: str, kagune_type: KaguneType
) -> tuple[bool, str]:
    """(успех, текст) — текст либо причина отказа, либо готовое сообщение об успехе."""
    ghoul_service = ctx.ghoul_service

    ghoul = await ghoul_service.get(find_by=telegram_id)
    if ghoul is None:
        return False, "Гуль не найден."

    current_strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
    if current_strength is None:
        return False, "Этот тип кагуне у тебя не открыт."

    user_cooldown = await ctx.cooldown_service.get_active_cooldown(
        telegram_id, "KAGUNE_UPGRADE"
    )
    if user_cooldown is not None:
        remaining = parse_seconds(int(user_cooldown.end_at - time.time()))
        return False, ctx.dialog_service.text(
            key="upgrade_kagune_cooldown_error",
            minutes=str(remaining.minutes_remaining),
            seconds=str(remaining.seconds_remaining),
        )

    price = ghoul_service.calculate_price_upgrade_kagune(current_strength)
    user = await ctx.user_service.get(find_by=telegram_id)
    if user is None:
        return False, "Пользователь не найден."

    if user.balance < price:
        return False, ctx.dialog_service.text(
            key="not_enough_money", money=int(price - user.balance) + 1
        )

    await ctx.user_service.minus_balance(
        telegram_id=telegram_id, change_balance=price, log="upgrade kagune"
    )
    new_ghoul = await ghoul_service.upgrade_kagune(telegram_id, kagune_type)
    await ctx.cooldown_service.set_cooldown(telegram_id, "KAGUNE_UPGRADE")

    new_strength = ghoul_service.get_kagune_strength(new_ghoul, kagune_type)
    text = ctx.dialog_service.text(
        key="upgrade_kagune_accept",
        name=first_name,
        kagune_strength=str(new_strength),
        money=str(price),
    )
    return True, text


def build_choice_keyboard(
    ctx: AppContext[Any], ghoul: Ghoul, owned: list[KaguneType], invoker_id: int
) -> tuple[str, InlineKeyboardMarkup]:
    """invoker_id зашивается прямо в callback_data — см. KaguneUpgradePress."""
    ghoul_service = ctx.ghoul_service
    lines = ["Какое кагуне усилить?"]
    keyboard = InlineKeyboard()

    for kagune_type in owned:
        strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
        price = ghoul_service.calculate_price_upgrade_kagune(strength or 0)
        label = f"{kagune_type.value['name']} - {price} CheSton"
        lines.append(f"{kagune_type.value['name']} (сила {strength}) - {price} CheSton")
        keyboard.button(
            label,
            KaguneUpgradePress(
                invoker_id=invoker_id, name_english=kagune_type.value["name_english"]
            ),
        )

    return "\n".join(lines), keyboard.markup()
