import logging

from selfrot import BaseRouter, MessageHandler
from selfrot.exceptions import TelegramAPIError
from selfrot.filter import HasMessageCallbackQuery, HasUser, Text
from selfrot.handlers import CallbackQueryHandler
from selfrot.types import Message

from src.bot.exceptions import GhoulNotFound

from ....context import AppContext
from ...types import DataMessageCallbackQuery, TextUserMessage
from .logic import become_kakuja, evolve_kagune
from .menu import build_menu
from .payloads import BecomeKakujaPress, BuyKagunePress

logger = logging.getLogger(__name__)


class EvolutionMenuHandler(MessageHandler[AppContext[TextUserMessage]]):
    query = (
        Text("эволюция", ignore_case=True)
        | Text("мутация", ignore_case=True)
        | Text("evolution", ignore_case=True)
        | Text("mutation", ignore_case=True)
    ) & HasUser()

    async def handle(self) -> None:
        ctx = self.ctx
        telegram_id = ctx.message.user.id

        ghoul = await ctx.ghoul_service.get(telegram_id)
        if ghoul is None:
            raise GhoulNotFound(telegram_id)

        rich_message, plain_text, keyboard = build_menu(ctx, ghoul, telegram_id)
        try:
            await ctx.message.answer_rich_message(rich_message=rich_message, reply_markup=keyboard)
        except TelegramAPIError:
            # answer_rich_or_text из routers/rich.py не передаёт reply_markup в запасной
            # текст: тут кнопки важны, поэтому свой запасной путь с той же клавиатурой.
            logger.warning("send_rich_message упал для эволюции, запасной текст", exc_info=True)
            await ctx.message.answer(plain_text, reply_markup=keyboard)


class BuyKaguneHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    press = BuyKagunePress.filter().pressed_by("invoker_id")
    query = press & HasMessageCallbackQuery()

    async def handle(self) -> None:
        ctx = self.ctx
        callback = ctx.callback_query
        message = callback.message
        if not isinstance(message, Message):
            return

        telegram_id = self.press.parse(ctx).invoker_id

        ok, line = await evolve_kagune(ctx, telegram_id)
        if not ok:
            await callback.answer(ctx.text(line), show_alert=True)
            return

        await callback.answer()
        await message.delete()
        await ctx.say(line)


class BecomeKakujaHandler(CallbackQueryHandler[AppContext[DataMessageCallbackQuery]]):
    press = BecomeKakujaPress.filter().pressed_by("invoker_id")
    query = press & HasMessageCallbackQuery()

    async def handle(self) -> None:
        ctx = self.ctx
        callback = ctx.callback_query
        message = callback.message
        if not isinstance(message, Message):
            return

        telegram_id = self.press.parse(ctx).invoker_id

        ok, line = await become_kakuja(ctx, telegram_id)
        if not ok:
            await callback.answer(ctx.text(line), show_alert=True)
            return

        await callback.answer()
        await message.delete()
        await ctx.say(line)


class EvolutionRouter(BaseRouter[AppContext]):
    handlers = (EvolutionMenuHandler, BuyKaguneHandler, BecomeKakujaHandler)
