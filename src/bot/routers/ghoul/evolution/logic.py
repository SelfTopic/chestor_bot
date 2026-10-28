from typing import Any, Optional

from src.bot.dialogs import Dialogs, Line
from src.bot.dialogs.vocab import KAGUNE_NAMES
from src.bot.exceptions import GhoulNotFound
from src.bot.game_configs import EVOLUTION_CONFIG
from src.bot.utils import format_amount

from ....context import AppContext

EVOLUTION = Dialogs.kagune.evolution


# Баланс и RC проверяются заново на каждую покупку: между показом меню и нажатием
# кнопки могло пройти время (тот же риск, что у растить кагуне/do_upgrade).
async def _charge(
    ctx: AppContext[Any], telegram_id: int, cheston: int, rc: int, log: str
) -> Optional[Line]:
    balance = await ctx.user_service.balance(telegram_id)
    if balance < cheston:
        return Dialogs.errors.not_enough_money(money=format_amount(cheston - balance))

    ghoul = await ctx.ghoul_service.get(telegram_id)
    if ghoul is None:
        raise GhoulNotFound(telegram_id)
    if ghoul.rc_money < rc:
        return Dialogs.errors.not_enough_rc(rc=format_amount(rc - ghoul.rc_money))

    await ctx.user_service.minus_balance(telegram_id=telegram_id, change_balance=cheston, log=log)
    await ctx.ghoul_service.increment_fields(telegram_id, rc_money=-rc)
    return None


async def evolve_kagune(ctx: AppContext[Any], telegram_id: int) -> tuple[bool, Line]:
    ghoul = await ctx.ghoul_service.get(telegram_id)
    if ghoul is None:
        raise GhoulNotFound(telegram_id)

    kagune_type = ctx.ghoul_service.next_missing_kagune_type(ghoul)
    if kagune_type is None:
        return False, EVOLUTION.all_kagune_done()

    price = EVOLUTION_CONFIG
    error = await _charge(
        ctx, telegram_id, price.new_kagune_cheston, price.new_kagune_rc, log="evolution: new kagune"
    )
    if error is not None:
        return False, error

    new_ghoul = await ctx.ghoul_service.grant_kagune_type(telegram_id, kagune_type)
    strength = ctx.ghoul_service.get_kagune_strength(new_ghoul, kagune_type)
    return True, EVOLUTION.kagune_done(
        kagune=KAGUNE_NAMES[kagune_type],
        strength=strength,
        cheston=format_amount(price.new_kagune_cheston),
        rc=format_amount(price.new_kagune_rc),
    )


async def become_kakuja(ctx: AppContext[Any], telegram_id: int) -> tuple[bool, Line]:
    ghoul = await ctx.ghoul_service.get(telegram_id)
    if ghoul is None:
        raise GhoulNotFound(telegram_id)

    if ghoul.is_kakuja:
        return False, EVOLUTION.already_kakuja()

    price = EVOLUTION_CONFIG
    error = await _charge(
        ctx, telegram_id, price.kakuja_cheston, price.kakuja_rc, log="evolution: kakuja"
    )
    if error is not None:
        return False, error

    await ctx.ghoul_service.become_kakuja(telegram_id)
    return True, EVOLUTION.kakuja_done(
        cheston=format_amount(price.kakuja_cheston), rc=format_amount(price.kakuja_rc)
    )
