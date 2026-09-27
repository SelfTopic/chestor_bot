import time
from typing import Any

from selfrot import InlineKeyboard
from selfrot.types import InlineKeyboardMarkup

from src.bot.dialogs import Dialogs, Line
from src.bot.types import KaguneType
from src.bot.utils import parse_seconds
from src.database.models import Ghoul

from ....context import AppContext
from .callback_data import KaguneUpgradePress


# Кулдаун и баланс проверяются заново: между показом клавиатуры и нажатием могло
# пройти время.
async def do_upgrade(
    ctx: AppContext[Any], telegram_id: int, kagune_type: KaguneType
) -> tuple[bool, Line]:
    ghoul_service = ctx.ghoul_service

    ghoul = await ghoul_service.get(find_by=telegram_id)
    if ghoul is None:
        return False, Dialogs.kagune.upgrade.no_ghoul()

    current_strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
    if current_strength is None:
        return False, Dialogs.kagune.upgrade.not_owned()

    user_cooldown = await ctx.cooldown_service.get_active_cooldown(
        telegram_id, "KAGUNE_UPGRADE"
    )
    if user_cooldown is not None:
        remaining = parse_seconds(int(user_cooldown.end_at - time.time()))
        return False, Dialogs.kagune.upgrade.cooldown(
            minutes=str(remaining.minutes_remaining),
            seconds=str(remaining.seconds_remaining),
        )

    price = ghoul_service.calculate_price_upgrade_kagune(current_strength)
    user = await ctx.user_service.get(find_by=telegram_id)
    if user is None:
        return False, Dialogs.kagune.upgrade.no_user()

    if user.balance < price:
        return False, Dialogs.errors.not_enough_money(
            money=int(price - user.balance) + 1
        )

    await ctx.user_service.minus_balance(
        telegram_id=telegram_id, change_balance=price, log="upgrade kagune"
    )
    new_ghoul = await ghoul_service.upgrade_kagune(telegram_id, kagune_type)
    await ctx.cooldown_service.set_cooldown(telegram_id, "KAGUNE_UPGRADE")

    new_strength = ghoul_service.get_kagune_strength(new_ghoul, kagune_type)
    return True, Dialogs.kagune.upgrade.done(
        kagune=kagune_type.value["name_english"],
        kagune_strength=str(new_strength),
        money=str(price),
    )


def build_choice_keyboard(
    ctx: AppContext[Any], ghoul: Ghoul, owned: list[KaguneType], invoker_id: int
) -> tuple[str, InlineKeyboardMarkup]:
    ghoul_service = ctx.ghoul_service
    choice = Dialogs.kagune.upgrade.choice
    rows: list[str] = []
    keyboard = InlineKeyboard()

    for kagune_type in owned:
        strength = ghoul_service.get_kagune_strength(ghoul, kagune_type)
        price = ghoul_service.calculate_price_upgrade_kagune(strength or 0)
        name = kagune_type.value["name"]
        rows.append(ctx.text(choice.row(kagune=name, strength=strength, price=price)))
        keyboard.button(
            ctx.text(choice.button(kagune=name, price=price)),
            KaguneUpgradePress(
                invoker_id=invoker_id, name_english=kagune_type.value["name_english"]
            ),
        )

    return ctx.text(choice.message(rows="\n".join(rows))), keyboard.markup()
