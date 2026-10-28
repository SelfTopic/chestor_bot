from typing import Any, get_args

from selfrot import BaseRouter, CallbackPayload, InlineKeyboard, MessageHandler, button
from selfrot.filter import HasMessageCallbackQuery, HasUser, Text
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import InlineKeyboardMarkup, Message

from src.bot.dialogs import Dialogs
from src.bot.dialogs.vocab import stat_label
from src.bot.game_configs import STAT_UPGRADE_CONFIG, STATS, StatKey, stat_cap_for_level
from src.bot.utils import format_amount
from src.database.models import Ghoul

from ...context import AppContext
from ..types import DataMessageCallbackQuery, TextUserMessage

STAT_KEYS: tuple[StatKey, ...] = get_args(StatKey)


class StatBuy(CallbackPayload, prefix="stat_buy"):
    stat: StatKey
    count: int


class StatNop(CallbackPayload, prefix="stat_nop"):
    pass


def build_shop(
    ctx: AppContext[Any], ghoul: Ghoul, balance: int
) -> tuple[str, InlineKeyboardMarkup]:
    rows: list[str] = []
    keyboard = InlineKeyboard()

    for key, emoji in STATS:
        assert key in STAT_KEYS
        current: int = getattr(ghoul, key)
        remaining = max(0, stat_cap_for_level(ghoul.level, key) - current)

        prices: list[str] = []
        buttons = []
        for multiplier in STAT_UPGRADE_CONFIG.multipliers:
            buy = min(multiplier, remaining)
            if buy <= 0:
                prices.append("—")
                buttons.append(button(f"{emoji} +{multiplier} (—)", StatNop()))
                continue

            price = STAT_UPGRADE_CONFIG.price(current, buy, key)
            prices.append(str(price))
            buttons.append(
                button(
                    f"{emoji} +{multiplier} ({price})",
                    StatBuy(stat=key, count=multiplier),
                )
            )

        rows.append(
            ctx.text(
                Dialogs.stats.shop.row(
                    stat=stat_label(ctx.text, key),
                    current=current,
                    x5=prices[1],
                    x10=prices[2],
                )
            )
        )
        keyboard.row(*buttons)

    text = Dialogs.stats.shop.message(balance=format_amount(balance), rows="\n".join(rows))
    return ctx.text(text), keyboard.markup()


class UpgradeStatHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("качаться", ignore_case=True) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        message = ctx.message

        if message.chat.type != "private":
            await ctx.say(Dialogs.stats.private_only(), reply=True)
            return

        ghoul = await ctx.db_ghoul()
        balance = await ctx.user_service.balance(message.user.id)
        text, keyboard = build_shop(ctx, ghoul, balance)
        await message.reply(text, reply_markup=keyboard)


async def _private_message(ctx: AppContext[Any]) -> Message | None:
    callback = ctx.callback_query
    message = callback.message

    if not isinstance(message, Message):
        await callback.answer(ctx.text(Dialogs.errors.cannot_process()))
        return None

    if message.chat.type != "private":
        await callback.answer(ctx.text(Dialogs.stats.private_only_action()))
        return None

    return message


class StatNopHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    query = StatNop.filter() & HasMessageCallbackQuery()

    async def handle(self) -> None:
        if await _private_message(self.ctx) is None:
            return

        await self.ctx.callback_query.answer(self.ctx.text(Dialogs.stats.limit()))


class StatBuyHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    press = StatBuy.filter()
    query = press & HasMessageCallbackQuery()

    async def handle(self) -> None:
        ctx = self.ctx
        callback = ctx.callback_query

        message = await _private_message(ctx)
        if message is None:
            return

        payload = self.press.parse(ctx)
        new_ghoul, bought, price = await ctx.stat_upgrade_service.purchase(
            telegram_id=callback.user.id, stat_key=payload.stat, count=payload.count
        )

        if bought == 0 and price > 0:
            await callback.answer(ctx.text(Dialogs.stats.no_money()))
            return

        if bought == 0 and price == 0:
            await callback.answer(ctx.text(Dialogs.stats.limit()))
            return

        balance = await ctx.user_service.balance(callback.user.id)
        text, keyboard = build_shop(ctx, new_ghoul, balance)
        await message.edit_text(text, reply_markup=keyboard)
        await callback.answer(
            ctx.text(
                Dialogs.stats.bought(
                    stat=stat_label(ctx.text, payload.stat), count=bought, price=price
                )
            )
        )


class UpgradeStatRouter(BaseRouter[AppContext]):
    handlers = (UpgradeStatHandler, StatNopHandler, StatBuyHandler)
