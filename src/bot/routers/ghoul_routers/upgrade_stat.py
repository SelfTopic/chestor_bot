"""
"качаться": магазин статов в личке с ботом. Покупку (цена, потолок уровня,
списание, +health вместе с max_health) делает StatUpgradeService.purchase(), текст
и кнопки магазина собираются здесь (build_shop).

Данные кнопок — типизированные StatBuy/StatNop вместо ручного разбора
"stat_buy_<stat>_<count>" у прода. Ответы прода на испорченные данные ("Неверные
данные кнопки", "Неверное количество", "Неверный стат") так недостижимы: наши кнопки
таких данных не дают, а чужие данные просто не подходят под фильтр и остаются без
ответа (как у малформных кнопок топа кагуне).
"""

from typing import Any, Literal, get_args

from selfrot import BaseRouter, CallbackPayload, InlineKeyboard, MessageHandler, button
from selfrot.filter import HasMessageCallbackQuery, HasUser, Text
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import InlineKeyboardMarkup, Message

from src.bot.game_configs import STAT_UPGRADE_CONFIG, STATS, stat_cap_for_level
from src.database.models import Ghoul, User

from ...context import AppContext
from ..types import DataMessageCallbackQuery, TextUserMessage

StatKey = Literal["strength", "dexterity", "speed", "max_health", "regeneration"]
STAT_KEYS: tuple[StatKey, ...] = get_args(StatKey)

# "💪Сила" и т.д.: подпись стата в ответе на покупку, как словарь allowed у прода
STAT_LABELS = {key: f"{emoji}{label}" for label, key, emoji in STATS}


class StatBuy(CallbackPayload, prefix="stat_buy"):
    stat: StatKey
    count: int


class StatNop(CallbackPayload, prefix="stat_nop"):
    """Кнопка стата, упёршегося в потолок уровня."""


def build_shop(ghoul: Ghoul, user: User | None) -> tuple[str, InlineKeyboardMarkup]:
    """Порт StatUpgradeService.build_message: те же строки и те же кнопки."""
    lines = [f"Баланс: {user.balance if user else 0}", ""]
    keyboard = InlineKeyboard()

    for label, key, emoji in STATS:
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

        lines.append(f"{emoji}{label}: {current}  х5: {prices[1]} х10: {prices[2]}")
        keyboard.row(*buttons)

    lines.append("")
    return "\n".join(lines), keyboard.markup()


class UpgradeStatHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = Text("качаться", ignore_case=True) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        message = ctx.message

        if message.chat.type != "private":
            await message.reply(
                "Эта команда работает только в личных сообщениях с ботом."
            )
            return

        ghoul = await ctx.db_ghoul()
        user = await ctx.user_service.get(find_by=message.user.id)
        text, keyboard = build_shop(ghoul, user)
        await message.reply(text, reply_markup=keyboard)


async def _private_message(ctx: AppContext[Any]) -> Message | None:
    """Сообщение под кнопкой, если с ним можно работать; иначе ответ, как у прода."""
    callback = ctx.callback_query
    message = callback.message

    if not isinstance(message, Message):
        await callback.answer("Невозможно обработать запрос")
        return None

    if message.chat.type != "private":
        await callback.answer("Эта операция доступна только в личных сообщениях.")
        return None

    return message


class StatNopHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    query = StatNop.filter() & HasMessageCallbackQuery()

    async def handle(self) -> None:
        if await _private_message(self.ctx) is None:
            return

        await self.ctx.callback_query.answer(
            "Достигнут предел прокачки для этого стата."
        )


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
        new_ghoul, new_user, bought, price = await ctx.stat_upgrade_service.purchase(
            telegram_id=callback.user.id, stat_key=payload.stat, count=payload.count
        )

        if bought == 0 and price > 0:
            await callback.answer("Недостаточно средств")
            return

        if bought == 0 and price == 0:
            await callback.answer("Достигнут предел прокачки для этого стата.")
            return

        text, keyboard = build_shop(new_ghoul, new_user)
        await message.edit_text(text, reply_markup=keyboard)
        await callback.answer(
            f"Прокачано {STAT_LABELS[payload.stat]} +{bought}. Потрачено: {price}"
        )


class UpgradeStatRouter(BaseRouter[AppContext]):
    handlers = (UpgradeStatHandler, StatNopHandler, StatBuyHandler)
